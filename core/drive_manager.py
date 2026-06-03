"""
Gerenciador de integração com Google Drive via Service Account.

Responsável por upload, download, listagem e remoção de CSVs na pasta
de dados da frota configurada no Drive.

Autenticação: Service Account cujas credenciais são lidas de
st.secrets["google_drive"] — funciona localmente via
.streamlit/secrets.toml e no Streamlit Community Cloud via
painel de secrets do projeto.
"""

from __future__ import annotations

import io
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

SCOPES = ["https://www.googleapis.com/auth/drive"]


# ---------------------------------------------------------------------------
# Autenticação e helpers internos
# ---------------------------------------------------------------------------

def _get_drive_service():
    """Retorna o cliente autenticado do Google Drive.

    Lê as credenciais de st.secrets["google_drive"]. O campo private_key
    armazenado no secrets.toml usa ``\\n`` literal — este método os converte
    para quebras de linha reais antes de criar as credenciais.
    """
    cfg = dict(st.secrets["google_drive"])
    cfg["private_key"] = cfg["private_key"].replace("\\n", "\n")
    creds = service_account.Credentials.from_service_account_info(
        cfg, scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _folder_id() -> str:
    """Retorna o ID da pasta do Drive configurado em st.secrets."""
    return st.secrets["google_drive"]["folder_id"]


# ---------------------------------------------------------------------------
# API pública — listagem e metadados
# ---------------------------------------------------------------------------

def listar_csvs_drive() -> list[dict]:
    """Lista todos os arquivos CSV na pasta configurada no Drive.

    Returns:
        Lista de dicts com campos: id, name, size, modifiedTime.
    """
    service = _get_drive_service()
    query = (
        f"'{_folder_id()}' in parents "
        "and mimeType='text/csv' "
        "and trashed=false"
    )
    resultado = (
        service.files()
        .list(
            q=query,
            fields="files(id, name, size, modifiedTime)",
            orderBy="name",
        )
        .execute()
    )
    return resultado.get("files", [])


def dados_disponiveis_drive() -> bool:
    """Retorna True se há pelo menos 1 CSV na pasta do Drive."""
    try:
        return len(listar_csvs_drive()) > 0
    except Exception:
        return False


# ---------------------------------------------------------------------------
# API pública — upload e remoção
# ---------------------------------------------------------------------------

def fazer_upload_csv(arquivo_bytes: bytes, nome_arquivo: str) -> str:
    """Faz upload de um CSV para a pasta do Drive.

    Se já existir um arquivo com o mesmo nome, substitui o conteúdo
    (update) em vez de criar um duplicado.

    Args:
        arquivo_bytes: Conteúdo do arquivo em bytes.
        nome_arquivo: Nome do arquivo com extensão .csv.

    Returns:
        file_id do arquivo criado ou atualizado no Drive.
    """
    service = _get_drive_service()
    existentes = listar_csvs_drive()
    mesmo_nome = next((f for f in existentes if f["name"] == nome_arquivo), None)

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="wb") as tmp:
        tmp.write(arquivo_bytes)
        tmp_path = Path(tmp.name)

    try:
        media = MediaFileUpload(str(tmp_path), mimetype="text/csv", resumable=True)

        if mesmo_nome:
            resultado = (
                service.files()
                .update(fileId=mesmo_nome["id"], media_body=media, fields="id")
                .execute()
            )
        else:
            metadata = {"name": nome_arquivo, "parents": [_folder_id()]}
            resultado = (
                service.files()
                .create(body=metadata, media_body=media, fields="id")
                .execute()
            )
    finally:
        tmp_path.unlink(missing_ok=True)

    return resultado["id"]


def remover_csv_drive(nome_arquivo: str) -> None:
    """Remove do Drive o arquivo CSV com o nome informado.

    Não lança exceção se o arquivo não for encontrado.
    """
    service = _get_drive_service()
    for f in listar_csvs_drive():
        if f["name"] == nome_arquivo:
            service.files().delete(fileId=f["id"]).execute()
            return


def limpar_csvs_drive() -> None:
    """Remove todos os arquivos CSV da pasta do Drive."""
    service = _get_drive_service()
    for f in listar_csvs_drive():
        try:
            service.files().delete(fileId=f["id"]).execute()
        except Exception as exc:
            print(f"drive_manager: erro ao deletar {f['name']}: {exc}")


# ---------------------------------------------------------------------------
# API pública — download e cache
# ---------------------------------------------------------------------------

@st.cache_data(ttl=600, show_spinner="Sincronizando dados do Drive...")
def baixar_todos_csvs() -> pd.DataFrame:
    """Baixa todos os CSVs da pasta do Drive, processa via core/loader.py
    e retorna DataFrame unificado.

    Como efeito colateral, semeia o banco DuckDB com os dados baixados para
    que as demais páginas possam executar consultas SQL via core/database.py.

    O resultado fica em cache por 600 segundos — use invalidar_cache_drive()
    para forçar uma nova sincronização.

    Returns:
        DataFrame consolidado com todas as rotas disponíveis no Drive.
    """
    from core.database import inicializar_banco, limpar_banco, registrar_csv
    from core.loader import load_csv_file

    arquivos = listar_csvs_drive()
    if not arquivos:
        return pd.DataFrame()

    service = _get_drive_service()
    inicializar_banco()
    limpar_banco()  # remove dados antigos para garantir consistência

    frames: list[pd.DataFrame] = []

    for arq in arquivos:
        try:
            request = service.files().get_media(fileId=arq["id"])
            buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(buffer, request)
            concluido = False
            while not concluido:
                _, concluido = downloader.next_chunk()
            buffer.seek(0)

            with tempfile.NamedTemporaryFile(
                suffix=".csv", delete=False, mode="wb"
            ) as tmp:
                tmp.write(buffer.read())
                tmp_path = Path(tmp.name)

            try:
                df = load_csv_file(tmp_path)
                if not df.empty:
                    registrar_csv(arq["name"], df)
                    frames.append(df)
            finally:
                tmp_path.unlink(missing_ok=True)

        except Exception as exc:
            print(f"drive_manager: erro ao baixar '{arq['name']}': {exc}")

    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def invalidar_cache_drive() -> None:
    """Limpa o cache de baixar_todos_csvs() para forçar nova sincronização."""
    baixar_todos_csvs.clear()
