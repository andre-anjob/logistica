"""Upload e gerenciamento de CSVs.

No modo Google Drive: os arquivos são enviados para a pasta do Drive
configurada em st.secrets e o DuckDB é semeado imediatamente.
No modo local: os arquivos são salvos em data/uploads/ e registrados
no DuckDB — comportamento original preservado.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st
from utils.styles import aplicar_estilos

from core.cache_manager import (
    UPLOADS_DIR,
    _drive_ativo,
    invalidar_cache,
    listar_arquivos_carregados,
)
from core.database import limpar_banco, registrar_csv, remover_csv
from core.loader import clean_tracking_dataframe
from utils.helpers import sanitize_filename


def main() -> None:
    """Renderiza upload e gerenciamento de dados."""
    st.set_page_config(layout="wide", page_title="Upload de Dados", page_icon="📤")
    aplicar_estilos()
    st.title("Upload de Dados")

    if _drive_ativo():
        st.info(
            "🌐 **Modo Google Drive ativo** — os arquivos enviados são armazenados "
            "na pasta do Drive configurada em secrets."
        )
    else:
        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

    try:
        uploaded_files = st.file_uploader(
            "Envie arquivos CSV de rastreamento",
            type=["csv"],
            accept_multiple_files=True,
        )

        if uploaded_files:
            for uploaded_file in uploaded_files:
                _processar_upload(uploaded_file)

        st.divider()
        st.subheader("Arquivos carregados")
        arquivos = listar_arquivos_carregados()
        if arquivos:
            st.dataframe(
                _formatar_arquivos(arquivos), use_container_width=True,
                hide_index=True,
            )
            _renderizar_remocoes(arquivos)
            st.divider()
            _renderizar_limpeza_total()
        else:
            st.info("Nenhum CSV carregado ainda.")
    except Exception as exc:
        st.error(f"Não foi possível processar os uploads: {exc}")


def _processar_upload(uploaded_file: object) -> None:
    """Valida o CSV, faz upload para o Drive ou disco local e registra no DuckDB."""
    nome = getattr(uploaded_file, "name", "arquivo.csv")
    bytes_csv = uploaded_file.getvalue()

    try:
        raw = _ler_csv_upload(bytes_csv)
        cleaned, invalid_coordinates, invalid_dates = clean_tracking_dataframe(raw)
        if cleaned.empty:
            st.error(f"❌ {nome}: arquivo válido, mas sem registros aproveitáveis.")
            return

        if _drive_ativo():
            from core.drive_manager import fazer_upload_csv
            fazer_upload_csv(bytes_csv, nome)
            # Insere imediatamente no DuckDB para que os filtros funcionem
            # sem aguardar o próximo ciclo de baixar_todos_csvs()
            registrar_csv(nome, cleaned)
            invalidar_cache()
        else:
            destino = _resolver_destino(nome)
            destino.write_bytes(bytes_csv)
            registrar_csv(destino.name, cleaned)
            invalidar_cache()

        st.success(
            f"✅ {nome}: {len(cleaned):,} registros válidos carregados. "
            f"{invalid_coordinates} coordenadas e {invalid_dates} datas "
            "inválidas descartadas."
        )
        st.dataframe(cleaned.head(5), use_container_width=True)
    except Exception as exc:
        st.error(f"❌ {nome}: não foi possível validar o CSV. {exc}")


def _ler_csv_upload(bytes_csv: bytes) -> pd.DataFrame:
    """Tenta ler o CSV com múltiplos encodings. Lança ValueError se falhar."""
    ultimo_erro: Exception | None = None
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin1"):
        try:
            return pd.read_csv(
                BytesIO(bytes_csv),
                sep=None,
                engine="python",
                dtype=str,
                encoding=encoding,
            )
        except Exception as exc:
            ultimo_erro = exc
    raise ValueError(f"Separador ou encoding não reconhecido. Erro: {ultimo_erro}")


def _resolver_destino(nome_original: str) -> Path:
    """Gera caminho de destino em data/uploads/, evitando colisões de nome."""
    stem = sanitize_filename(Path(nome_original).stem)
    destino = UPLOADS_DIR / f"{stem}.csv"
    contador = 2
    while destino.exists():
        destino = UPLOADS_DIR / f"{stem}_{contador}.csv"
        contador += 1
    return destino


def _formatar_arquivos(arquivos: list[dict]) -> list[dict]:
    """Formata a lista de metadados para exibição no st.dataframe."""
    linhas = []
    for item in arquivos:
        upload_ts = item["data_upload"]
        upload_str = (
            upload_ts.strftime("%d/%m/%Y %H:%M")
            if pd.notna(upload_ts)
            else "—"
        )
        linhas.append(
            {
                "Nome": item["nome"],
                "Tamanho (KB)": item["tamanho_kb"],
                "Upload": upload_str,
                "Período início": item["periodo_inicio"],
                "Período fim": item["periodo_fim"],
                "Veículos": item["veiculos"],
                "Registros": item["total_registros"],
                "Status": "Válido" if item["valido"] else "Inválido",
            }
        )
    return linhas


def _renderizar_remocoes(arquivos: list[dict]) -> None:
    """Renderiza botões de remoção individual com confirmação."""
    st.subheader("Remover arquivo")
    for item in arquivos:
        col_nome, col_botao = st.columns([4, 1])
        with col_nome:
            st.write(item["nome"])
        with col_botao:
            if st.button("🗑️ Remover", key=f"remover_{item['nome']}"):
                st.session_state[f"confirmar_{item['nome']}"] = True

        if st.session_state.get(f"confirmar_{item['nome']}", False):
            st.warning(f"Confirmar remoção de **{item['nome']}**?")
            confirmar, cancelar = st.columns(2)
            with confirmar:
                if st.button("Confirmar", key=f"confirmar_sim_{item['nome']}"):
                    if _drive_ativo():
                        from core.drive_manager import remover_csv_drive
                        remover_csv_drive(item["nome"])
                    else:
                        caminho = UPLOADS_DIR / item["nome"]
                        if caminho.exists():
                            caminho.unlink()
                    remover_csv(item["nome"])
                    invalidar_cache()
                    st.session_state[f"confirmar_{item['nome']}"] = False
                    st.rerun()
            with cancelar:
                if st.button("Cancelar", key=f"confirmar_nao_{item['nome']}"):
                    st.session_state[f"confirmar_{item['nome']}"] = False
                    st.rerun()


def _renderizar_limpeza_total() -> None:
    """Renderiza botão de limpeza total com confirmação."""
    if st.button("🧹 Limpar todos"):
        st.session_state["confirmar_limpeza_total"] = True

    if st.session_state.get("confirmar_limpeza_total", False):
        st.warning("Confirmar remoção de **todos** os CSVs carregados?")
        confirmar, cancelar = st.columns(2)
        with confirmar:
            if st.button("Confirmar limpeza"):
                if _drive_ativo():
                    from core.drive_manager import limpar_csvs_drive
                    limpar_csvs_drive()
                else:
                    for csv_path in UPLOADS_DIR.glob("*.csv"):
                        csv_path.unlink()
                limpar_banco()
                invalidar_cache()
                st.session_state["confirmar_limpeza_total"] = False
                st.rerun()
        with cancelar:
            if st.button("Cancelar limpeza"):
                st.session_state["confirmar_limpeza_total"] = False
                st.rerun()


main()

# ALTERAÇÕES:
# - _processar_upload(): modo Drive → fazer_upload_csv() + registrar_csv()
#   imediato no DuckDB + invalidar_cache(); modo local → fluxo original.
# - _renderizar_remocoes(): modo Drive → remover_csv_drive() antes de
#   remover_csv() no DuckDB; modo local → unlink() original.
# - _renderizar_limpeza_total(): modo Drive → limpar_csvs_drive() antes de
#   limpar_banco(); modo local → unlink() original.
# - Banner informativo quando Drive está ativo.
# - _formatar_arquivos(): trata data_upload NaT (vindo do Drive) sem erro.



