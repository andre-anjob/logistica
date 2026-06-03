"""Camada de acesso ao banco DuckDB do portal logístico."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

# Garante que o console Windows aceita os emojis dos prints de core/loader.py
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

DB_PATH = Path("data") / "frota.duckdb"
UPLOADS_DIR = Path("data") / "uploads"

_DDL = """
CREATE TABLE IF NOT EXISTS frota (
    veiculo          TEXT,
    placa            TEXT,
    organizacao      TEXT,
    data_coordenada  TIMESTAMP,
    velocidade       DOUBLE,
    ignicao          TEXT,
    latitude         DOUBLE,
    longitude        DOUBLE,
    data_rota        DATE,
    arquivo_origem   TEXT
)
"""


def obter_conexao() -> duckdb.DuckDBPyConnection:
    """Retorna conexão com o banco DuckDB local (cria o arquivo se não existir)."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(DB_PATH))


def inicializar_banco() -> None:
    """Cria a tabela `frota` se ainda não existir."""
    with obter_conexao() as con:
        con.execute(_DDL)


def sincronizar_uploads() -> None:
    """Sincroniza o banco com os arquivos em data/uploads/.

    - CSVs em disco que não estão no banco → carregar e inserir.
    - Entradas no banco cujo arquivo não existe mais em disco → deletar.
    """
    from core.loader import load_csv_file  # importação local evita ciclo

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    arquivos_disco = {p.name for p in UPLOADS_DIR.glob("*.csv")}

    with obter_conexao() as con:
        resultado = con.execute(
            "SELECT DISTINCT arquivo_origem FROM frota"
        ).fetchall()
        arquivos_banco = {row[0] for row in resultado}

        # remove entradas cujo CSV foi deletado do disco
        for nome in arquivos_banco - arquivos_disco:
            con.execute("DELETE FROM frota WHERE arquivo_origem = ?", [nome])

        # insere CSVs novos que ainda não estão no banco
        for nome in arquivos_disco - arquivos_banco:
            try:
                df = load_csv_file(UPLOADS_DIR / nome)
                if not df.empty:
                    _inserir_dataframe(con, nome, df)
            except (FileNotFoundError, ValueError, OSError) as exc:
                print(f"sincronizar_uploads: ignorado {nome}. Motivo: {exc}")


def registrar_csv(nome_arquivo: str, df: pd.DataFrame) -> int:
    """Remove registros anteriores do arquivo e insere o DataFrame no banco.

    Args:
        nome_arquivo: Nome do arquivo CSV (chave de origem).
        df: DataFrame limpo retornado por core/loader.py.

    Returns:
        Quantidade de registros inseridos.
    """
    with obter_conexao() as con:
        con.execute("DELETE FROM frota WHERE arquivo_origem = ?", [nome_arquivo])
        inseridos = _inserir_dataframe(con, nome_arquivo, df)
    return inseridos


def remover_csv(nome_arquivo: str) -> None:
    """Remove do banco todos os registros do arquivo informado."""
    with obter_conexao() as con:
        con.execute("DELETE FROM frota WHERE arquivo_origem = ?", [nome_arquivo])


def limpar_banco() -> None:
    """Remove todos os registros da tabela frota."""
    with obter_conexao() as con:
        con.execute("DELETE FROM frota")


def banco_vazio() -> bool:
    """Retorna True se a tabela frota não tiver nenhum registro."""
    with obter_conexao() as con:
        total = con.execute("SELECT COUNT(*) FROM frota").fetchone()[0]
    return total == 0


def consultar_periodo() -> tuple[date, date] | None:
    """Retorna (data_min, data_max) dos registros no banco. None se vazio."""
    with obter_conexao() as con:
        row = con.execute(
            "SELECT MIN(data_rota), MAX(data_rota) FROM frota"
        ).fetchone()
    if row is None or row[0] is None:
        return None
    return row[0], row[1]


def consultar_veiculos() -> list[str]:
    """Retorna lista ordenada de veículos únicos no banco."""
    with obter_conexao() as con:
        rows = con.execute(
            "SELECT DISTINCT veiculo FROM frota WHERE veiculo IS NOT NULL ORDER BY veiculo"
        ).fetchall()
    return [row[0] for row in rows]


def consultar_organizacoes() -> list[str]:
    """Retorna lista ordenada de organizações únicas no banco."""
    with obter_conexao() as con:
        rows = con.execute(
            "SELECT DISTINCT organizacao FROM frota WHERE organizacao IS NOT NULL ORDER BY organizacao"
        ).fetchall()
    return [row[0] for row in rows]


def consultar_dados(
    data_inicio: date,
    data_fim: date,
    veiculos: list[str] | None = None,
    organizacoes: list[str] | None = None,
) -> pd.DataFrame:
    """Consulta registros filtrados e retorna DataFrame pandas com colunas em português.

    Args:
        data_inicio: Data inicial do filtro (inclusive).
        data_fim: Data final do filtro (inclusive).
        veiculos: Lista de veículos para filtrar. None = todos.
        organizacoes: Lista de organizações para filtrar. None = todas.

    Returns:
        DataFrame com nomes de colunas compatíveis com o restante do sistema.
    """
    params: list = [data_inicio, data_fim]
    filtros_extras = ["data_rota BETWEEN ? AND ?"]

    if veiculos:
        placeholders = ", ".join(["?"] * len(veiculos))
        filtros_extras.append(f"veiculo IN ({placeholders})")
        params.extend(veiculos)

    if organizacoes:
        placeholders = ", ".join(["?"] * len(organizacoes))
        filtros_extras.append(f"organizacao IN ({placeholders})")
        params.extend(organizacoes)

    where = " AND ".join(filtros_extras)
    sql = f"""
        SELECT
            veiculo          AS "Veículo",
            placa            AS "Placa",
            organizacao      AS "Organização",
            data_coordenada  AS "Data da Coordenada",
            velocidade       AS "Velocidade",
            ignicao          AS "Ignição",
            latitude,
            longitude,
            data_rota
        FROM frota
        WHERE {where}
        ORDER BY veiculo, data_coordenada
    """
    with obter_conexao() as con:
        df = con.execute(sql, params).df()

    # Garante tipos compatíveis com o restante do sistema
    if not df.empty:
        df["Data da Coordenada"] = pd.to_datetime(df["Data da Coordenada"])
        df["data_rota"] = pd.to_datetime(df["data_rota"]).dt.date
        for col in ["Veículo", "Placa", "Organização", "Ignição"]:
            df[col] = df[col].astype("category")

    return df


def consultar_resumo_diario_sql(
    data_inicio: date,
    data_fim: date,
    veiculos: list[str] | None = None,
    organizacoes: list[str] | None = None,
    speed_limit: float = 80.0,
) -> pd.DataFrame:
    """Calcula resumo diário agregado diretamente no DuckDB via SQL.

    Retorna uma linha por (veiculo, placa, data_rota) com km_total,
    velocidade_media, velocidade_maxima, alertas_velocidade,
    total_registros, inicio e fim.

    Args:
        data_inicio: Data inicial do filtro.
        data_fim: Data final do filtro.
        veiculos: Lista de veículos para filtrar. None = todos.
        organizacoes: Lista de organizações para filtrar. None = todas.
        speed_limit: Limite de velocidade para alertas.
    """
    params: list = [data_inicio, data_fim]
    filtros_extras = ["data_rota BETWEEN ? AND ?"]

    if veiculos:
        placeholders = ", ".join(["?"] * len(veiculos))
        filtros_extras.append(f"veiculo IN ({placeholders})")
        params.extend(veiculos)

    if organizacoes:
        placeholders = ", ".join(["?"] * len(organizacoes))
        filtros_extras.append(f"organizacao IN ({placeholders})")
        params.extend(organizacoes)

    where = " AND ".join(filtros_extras)
    params.append(speed_limit)

    sql = f"""
        WITH pontos AS (
            SELECT *,
                LAG(latitude)  OVER w AS lat_ant,
                LAG(longitude) OVER w AS lon_ant
            FROM frota
            WHERE {where}
            WINDOW w AS (
                PARTITION BY veiculo, placa, data_rota
                ORDER BY data_coordenada
            )
        ),
        dist AS (
            SELECT *,
                CASE WHEN lat_ant IS NULL THEN 0.0
                ELSE 2 * 6371.0088 * asin(sqrt(
                    power(sin(radians(latitude  - lat_ant) / 2), 2) +
                    cos(radians(lat_ant)) * cos(radians(latitude)) *
                    power(sin(radians(longitude - lon_ant) / 2), 2)
                )) END AS dist_km
            FROM pontos
        )
        SELECT
            veiculo                                             AS "Veículo",
            placa                                               AS "Placa",
            data_rota,
            SUM(dist_km)                                        AS km_total,
            AVG(CASE WHEN velocidade > 0 THEN velocidade END)   AS velocidade_media,
            MAX(velocidade)                                     AS velocidade_maxima,
            COUNT(CASE WHEN velocidade > ? THEN 1 END)          AS alertas_velocidade,
            COUNT(*)                                            AS total_registros,
            MIN(data_coordenada)                                AS inicio,
            MAX(data_coordenada)                                AS fim
        FROM dist
        GROUP BY veiculo, placa, data_rota
        ORDER BY veiculo, data_rota
    """
    with obter_conexao() as con:
        df = con.execute(sql, params).df()

    if not df.empty:
        df["data_rota"] = pd.to_datetime(df["data_rota"]).dt.date
        df["inicio"] = pd.to_datetime(df["inicio"])
        df["fim"] = pd.to_datetime(df["fim"])
        df["alertas_velocidade"] = df["alertas_velocidade"].astype(int)
        df["total_registros"] = df["total_registros"].astype(int)

    return df


def listar_arquivos_no_banco() -> list[dict]:
    """Retorna metadados dos arquivos registrados no banco."""
    sql = """
        SELECT
            arquivo_origem          AS nome,
            COUNT(*)                AS total_registros,
            MIN(data_rota)          AS periodo_inicio,
            MAX(data_rota)          AS periodo_fim,
            COUNT(DISTINCT veiculo) AS veiculos
        FROM frota
        GROUP BY arquivo_origem
        ORDER BY arquivo_origem
    """
    with obter_conexao() as con:
        rows = con.execute(sql).fetchall()

    return [
        {
            "nome": row[0],
            "total_registros": int(row[1]),
            "periodo_inicio": row[2],
            "periodo_fim": row[3],
            "veiculos": int(row[4]),
        }
        for row in rows
    ]


def _inserir_dataframe(
    con: duckdb.DuckDBPyConnection, nome_arquivo: str, df: pd.DataFrame
) -> int:
    """Insere um DataFrame limpo na tabela frota. Retorna o número de linhas inseridas."""
    df_ins = df.copy()

    # Normaliza nomes de colunas para os nomes do banco
    rename = {
        "Veículo": "veiculo",
        "Placa": "placa",
        "Organização": "organizacao",
        "Data da Coordenada": "data_coordenada",
        "Velocidade": "velocidade",
        "Ignição": "ignicao",
        "latitude": "latitude",
        "longitude": "longitude",
        "data_rota": "data_rota",
    }
    df_ins = df_ins.rename(columns=rename)
    colunas_banco = list(rename.values())
    df_ins = df_ins[[c for c in colunas_banco if c in df_ins.columns]].copy()

    # Converte categoricals para string antes de inserir
    for col in ["veiculo", "placa", "organizacao", "ignicao"]:
        if col in df_ins.columns and hasattr(df_ins[col], "cat"):
            df_ins[col] = df_ins[col].astype(str)

    df_ins["arquivo_origem"] = nome_arquivo

    con.register("_df_temp", df_ins)
    con.execute("INSERT INTO frota SELECT * FROM _df_temp")
    con.unregister("_df_temp")

    return len(df_ins)

# ALTERAÇÕES:
# - Arquivo criado do zero: implementa toda a camada DuckDB.
# - obter_conexao: abre (ou cria) data/frota.duckdb.
# - inicializar_banco: CREATE TABLE IF NOT EXISTS frota com os 10 campos.
# - sincronizar_uploads: compara disco vs banco; insere novos, remove deletados.
# - registrar_csv / remover_csv / limpar_banco: operações CRUD por arquivo.
# - banco_vazio / consultar_periodo / consultar_veiculos / consultar_organizacoes:
#   metadados sem carregar linhas na memória.
# - consultar_dados: SELECT com WHERE dinâmico; renomeia para colunas em português.
# - consultar_resumo_diario_sql: haversine via LAG() + GROUP BY direto no DuckDB.
# - listar_arquivos_no_banco: GROUP BY arquivo_origem para metadados.
# - _inserir_dataframe: helper interno; normaliza nomes e usa register/INSERT.
