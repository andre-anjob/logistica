"""Carregamento e limpeza inicial de arquivos CSV de rastreamento."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

import pandas as pd

from config import (
    BRAZILIAN_DATETIME_FORMAT,
    DATE_COLUMNS,
    EXPECTED_COLUMNS,
    LATITUDE_COLUMN,
    LONGITUDE_COLUMN,
    ROUTE_DATE_COLUMN,
)
from utils.helpers import parse_float

ENCODINGS_TO_TRY = ("utf-8-sig", "utf-8", "cp1252", "latin1")


def load_csv_file(path: str | Path) -> pd.DataFrame:
    """Carrega um CSV, detecta separador e devolve um DataFrame limpo.

    Args:
        path: Caminho do arquivo CSV.

    Returns:
        DataFrame tipado, com colunas ``latitude`` e ``longitude``.

    Raises:
        FileNotFoundError: Quando o arquivo não existe.
        ValueError: Quando o CSV não contém as colunas esperadas.
    """
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV não encontrado: {csv_path}")
    if not csv_path.is_file():
        raise ValueError(f"O caminho informado não é um arquivo: {csv_path}")

    raw = _read_csv_with_auto_detection(csv_path)
    cleaned, invalid_coordinates, invalid_dates = clean_tracking_dataframe(raw)

    print(
        "✅ "
        f"{len(cleaned):,}".replace(",", ".")
        + f" registros carregados de {csv_path.name}"
    )
    if invalid_coordinates:
        print(
            "ℹ️ "
            f"{invalid_coordinates:,}".replace(",", ".")
            + " registros com coordenadas inválidas descartados"
        )
    if invalid_dates:
        print(
            "ℹ️ "
            f"{invalid_dates:,}".replace(",", ".")
            + " registros com data inválida descartados"
        )

    return cleaned


def load_csv_folder(folder: str | Path) -> pd.DataFrame:
    """Carrega todos os CSVs de uma pasta.

    Args:
        folder: Pasta que contém arquivos ``.csv``.

    Returns:
        DataFrame único com todos os registros limpos.

    Raises:
        FileNotFoundError: Quando a pasta não existe ou não contém CSVs.
    """
    folder_path = Path(folder)
    if not folder_path.exists():
        raise FileNotFoundError(f"Pasta não encontrada: {folder_path}")
    if not folder_path.is_dir():
        raise ValueError(f"O caminho informado não é uma pasta: {folder_path}")

    csv_files = sorted(folder_path.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"Nenhum arquivo CSV encontrado em: {folder_path}")

    frames = [load_csv_file(csv_file) for csv_file in csv_files]
    combined = pd.concat(frames, ignore_index=True)
    print("✅ Total consolidado: " + f"{len(combined):,}".replace(",", ".") + " registros")
    return combined


def clean_tracking_dataframe(raw: pd.DataFrame) -> tuple[pd.DataFrame, int, int]:
    """Limpa e tipa um DataFrame bruto de rastreamento.

    Args:
        raw: DataFrame lido do CSV.

    Returns:
        Tupla com DataFrame limpo, quantidade de coordenadas inválidas e datas
        inválidas descartadas.

    Raises:
        ValueError: Quando faltam colunas obrigatórias.
    """
    df = raw.copy()
    df.columns = [str(column).strip().lstrip("\ufeff") for column in df.columns]

    missing = [column for column in EXPECTED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(
            "CSV com colunas obrigatórias ausentes: "
            + ", ".join(missing)
            + ". Verifique cabeçalho, encoding e separador."
        )

    df = df[EXPECTED_COLUMNS].copy()

    for column in ["Veículo", "Placa", "Organização", "Ignição", "Serial", "Posição"]:
        df[column] = df[column].fillna("").astype(str).str.strip()

    coords = (
        df["Posição"]
        .astype(str)
        .str.replace('"', "", regex=False)
        .str.strip()
        .str.extract(r"^\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*$")
    )
    df[LATITUDE_COLUMN] = pd.to_numeric(coords[0], errors="coerce")
    df[LONGITUDE_COLUMN] = pd.to_numeric(coords[1], errors="coerce")

    out_of_range = (
        (df[LATITUDE_COLUMN] < -90) | (df[LATITUDE_COLUMN] > 90)
        | (df[LONGITUDE_COLUMN] < -180) | (df[LONGITUDE_COLUMN] > 180)
    )
    df.loc[out_of_range, [LATITUDE_COLUMN, LONGITUDE_COLUMN]] = None

    valid_coordinates = df[LATITUDE_COLUMN].notna() & df[LONGITUDE_COLUMN].notna()
    invalid_coordinates = int((~valid_coordinates).sum())
    df = df.loc[valid_coordinates].copy()

    for column in DATE_COLUMNS:
        df[column] = pd.to_datetime(
            df[column],
            format=BRAZILIAN_DATETIME_FORMAT,
            errors="coerce",
            dayfirst=True,
        )

    invalid_dates = int(df["Data da Coordenada"].isna().sum())
    df = df.dropna(subset=["Data da Coordenada"]).copy()

    df["Velocidade"] = df["Velocidade"].map(parse_float).fillna(0.0).astype(float)
    df[ROUTE_DATE_COLUMN] = df["Data da Coordenada"].dt.date

    for col in ["Veículo", "Placa", "Organização", "Ignição"]:
        df[col] = df[col].astype("category")

    return df.reset_index(drop=True), invalid_coordinates, invalid_dates


def _read_csv_with_auto_detection(path: Path) -> pd.DataFrame:
    last_error: Exception | None = None

    for encoding in ENCODINGS_TO_TRY:
        try:
            separator = detect_separator(path, encoding)
            _engine = "c" if separator in (",", ";") else "python"
            dataframe = pd.read_csv(
                path,
                sep=separator,
                encoding=encoding,
                engine=_engine,
                dtype=str,
                quotechar='"',
                on_bad_lines="warn",
            )
            dataframe.columns = [
                str(column).strip().lstrip("\ufeff") for column in dataframe.columns
            ]
            if all(column in dataframe.columns for column in EXPECTED_COLUMNS):
                return dataframe
            last_error = ValueError(
                "Cabeçalho lido, mas colunas esperadas não foram encontradas."
            )
        except UnicodeDecodeError as exc:
            last_error = exc
        except (pd.errors.ParserError, csv.Error, OSError, ValueError) as exc:
            last_error = exc

    raise ValueError(
        f"Não foi possível ler o CSV {path}. Erro: {last_error}"
    ) from last_error


def detect_separator(path: Path, encoding: str) -> str:
    """Detecta o separador de um CSV entre vírgula e ponto-e-vírgula.

    Args:
        path: Caminho do CSV.
        encoding: Encoding usado para ler a amostra.

    Returns:
        Separador detectado.
    """
    sample = _read_text_sample(path, encoding)
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;")
        return dialect.delimiter
    except csv.Error:
        first_line = sample.splitlines()[0] if sample.splitlines() else ""
        return ";" if first_line.count(";") > first_line.count(",") else ","


def _read_text_sample(path: Path, encoding: str, size: int = 8192) -> str:
    with path.open("r", encoding=encoding, newline="") as file:
        return file.read(size)


def load_many(paths: Iterable[str | Path]) -> pd.DataFrame:
    """Carrega vários CSVs informados explicitamente.

    Args:
        paths: Lista de caminhos de CSV.

    Returns:
        DataFrame consolidado.
    """
    frames = [load_csv_file(path) for path in paths]
    if not frames:
        return pd.DataFrame(columns=EXPECTED_COLUMNS)
    return pd.concat(frames, ignore_index=True)
