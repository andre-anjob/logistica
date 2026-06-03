"""Gerenciamento de dados do portal.

Modo de operação detectado automaticamente:
  - Drive ativo  (st.secrets contém [google_drive]): dados vindos do Google
    Drive via core/drive_manager.py; DuckDB semeado a partir do Drive.
  - Modo local (sem secrets): dados lidos de data/uploads/; DuckDB
    sincronizado a partir dos arquivos locais.

Todas as assinaturas públicas são idênticas em ambos os modos, garantindo
que nenhuma página precise ser alterada.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from core.database import (
    banco_vazio,
    consultar_dados,
    consultar_periodo,
    inicializar_banco,
    listar_arquivos_no_banco,
    sincronizar_uploads,
)

UPLOADS_DIR = Path("data") / "uploads"


# ---------------------------------------------------------------------------
# Detecção de modo
# ---------------------------------------------------------------------------

def _drive_ativo() -> bool:
    """Retorna True quando o Google Drive está configurado via st.secrets.

    Funciona tanto em contexto Streamlit (local ou Cloud) quanto fora dele
    (testes, CLI) — nesse último caso retorna False sem lançar exceção.
    """
    try:
        import streamlit as st
        return "google_drive" in st.secrets
    except Exception:
        return False


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def carregar_dados_consolidados() -> pd.DataFrame:
    """Retorna todos os dados disponíveis (Drive ou disco local).

    No modo Drive: baixa todos os CSVs do Google Drive via drive_manager,
    semeia o DuckDB e retorna o DataFrame consolidado.
    No modo local: sincroniza o DuckDB com data/uploads/ e retorna os dados
    consultados via SQL.
    """
    if _drive_ativo():
        from core.drive_manager import baixar_todos_csvs
        return baixar_todos_csvs()

    # Modo local
    inicializar_banco()
    sincronizar_uploads()
    periodo = consultar_periodo()
    if periodo is None:
        return pd.DataFrame()
    return consultar_dados(periodo[0], periodo[1])


def invalidar_cache() -> None:
    """Força ressincronização dos dados.

    No modo Drive: limpa o cache do drive_manager para que o próximo acesso
    baixe tudo novamente.
    No modo local: sincroniza o DuckDB com os arquivos em data/uploads/.
    """
    if _drive_ativo():
        from core.drive_manager import invalidar_cache_drive
        invalidar_cache_drive()
        return

    inicializar_banco()
    sincronizar_uploads()


def listar_arquivos_carregados() -> list[dict]:
    """Lista metadados dos arquivos disponíveis.

    Retorna os mesmos campos em ambos os modos para compatibilidade total
    com os callers existentes:
    nome, tamanho_kb, data_upload, periodo_inicio, periodo_fim,
    veiculos, total_registros, valido, erro.

    No modo Drive: metadados do Drive cruzados com os do DuckDB.
    No modo local: metadados do disco cruzados com os do DuckDB.
    """
    if _drive_ativo():
        return _listar_arquivos_drive()

    return _listar_arquivos_local()


def dados_disponiveis() -> bool:
    """Retorna True se há pelo menos um registro de rota disponível.

    No modo Drive: verifica se há CSVs no Drive e garante que o DuckDB
    esteja semeado (chamando baixar_todos_csvs() se necessário).
    No modo local: sincroniza e verifica o DuckDB.
    """
    if _drive_ativo():
        from core.drive_manager import baixar_todos_csvs, dados_disponiveis_drive
        if not dados_disponiveis_drive():
            return False
        # Garante que o DuckDB está semeado para as consultas das outras páginas
        baixar_todos_csvs()
        return not banco_vazio()

    inicializar_banco()
    sincronizar_uploads()
    return not banco_vazio()


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _listar_arquivos_drive() -> list[dict]:
    """Lista arquivos no modo Google Drive."""
    from core.drive_manager import listar_csvs_drive

    arquivos_drive = listar_csvs_drive()
    banco = {item["nome"]: item for item in listar_arquivos_no_banco()}

    resultado: list[dict] = []
    for arq in arquivos_drive:
        nome = arq["name"]
        info = banco.get(nome, {})
        try:
            data_upload = pd.Timestamp(arq.get("modifiedTime", ""))
        except Exception:
            data_upload = pd.NaT
        resultado.append(
            {
                "nome": nome,
                "tamanho_kb": round(int(arq.get("size", 0)) / 1024, 1),
                "data_upload": data_upload,
                "periodo_inicio": info.get("periodo_inicio"),
                "periodo_fim": info.get("periodo_fim"),
                "veiculos": info.get("veiculos", 0),
                "total_registros": info.get("total_registros", 0),
                "valido": nome in banco,
                "erro": "",
            }
        )
    return resultado


def _listar_arquivos_local() -> list[dict]:
    """Lista arquivos no modo local (data/uploads/)."""
    inicializar_banco()
    banco = {item["nome"]: item for item in listar_arquivos_no_banco()}
    arquivos: list[dict] = []
    for csv_path in sorted(UPLOADS_DIR.glob("*.csv")):
        info = banco.get(csv_path.name, {})
        arquivos.append(
            {
                "nome": csv_path.name,
                "tamanho_kb": round(csv_path.stat().st_size / 1024, 1),
                "data_upload": pd.Timestamp.fromtimestamp(csv_path.stat().st_mtime),
                "periodo_inicio": info.get("periodo_inicio"),
                "periodo_fim": info.get("periodo_fim"),
                "veiculos": info.get("veiculos", 0),
                "total_registros": info.get("total_registros", 0),
                "valido": csv_path.name in banco,
                "erro": "",
            }
        )
    return arquivos

# ALTERAÇÕES:
# - Adicionado _drive_ativo(): detecta automaticamente se o Google Drive está
#   configurado via st.secrets["google_drive"].
# - carregar_dados_consolidados(): modo Drive → baixar_todos_csvs();
#   modo local → fluxo DuckDB original (inalterado).
# - invalidar_cache(): modo Drive → invalidar_cache_drive();
#   modo local → sincronizar_uploads() (inalterado).
# - listar_arquivos_carregados(): modo Drive → _listar_arquivos_drive() com
#   metadados do Drive cruzados com DuckDB; modo local → _listar_arquivos_local()
#   (lógica original extraída para helper).
# - dados_disponiveis(): modo Drive → verifica Drive + semeia DuckDB;
#   modo local → lógica original (inalterada).
# - Assinaturas públicas e UPLOADS_DIR 100% preservados.
