"""Funções auxiliares para parsing, distâncias e formatação."""

from __future__ import annotations

import math
import re
import unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from config import BRAZILIAN_DATE_FORMAT


def parse_float(value: Any) -> float | None:
    """Converte valores numéricos brasileiros ou internacionais para float.

    Args:
        value: Valor bruto vindo do CSV.

    Returns:
        Float convertido ou None quando o valor é inválido.
    """
    if value is None:
        return None

    text = str(value).strip().replace('"', "").replace("'", "")
    if not text or text.lower() in {"nan", "none", "null"}:
        return None

    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(",", ".")

    try:
        return float(text)
    except ValueError:
        return None


def parse_position(value: Any) -> tuple[float, float] | None:
    """Extrai latitude e longitude de uma string no formato ``latitude,longitude``.

    Args:
        value: Conteúdo bruto da coluna ``Posição``.

    Returns:
        Tupla ``(latitude, longitude)`` ou None quando a coordenada é inválida.
    """
    if value is None:
        return None

    text = str(value).strip().replace('"', "").replace("'", "")
    if not text or text.lower() in {"nan", "none", "null"}:
        return None

    parts = [part.strip() for part in text.split(",")]
    if len(parts) != 2:
        return None

    latitude = parse_float(parts[0])
    longitude = parse_float(parts[1])
    if latitude is None or longitude is None:
        return None

    if not is_valid_coordinate(latitude, longitude):
        return None

    return latitude, longitude


def is_valid_coordinate(latitude: float, longitude: float) -> bool:
    """Valida se latitude e longitude estão dentro dos ranges geográficos.

    Args:
        latitude: Latitude em graus decimais.
        longitude: Longitude em graus decimais.

    Returns:
        True quando a coordenada é válida.
    """
    return -90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0


def parse_brazilian_date(value: str) -> date:
    """Converte data no formato brasileiro ``dd/mm/yyyy`` para ``date``.

    Args:
        value: Texto da data.

    Returns:
        Data convertida.

    Raises:
        ValueError: Quando o valor não segue o formato esperado.
    """
    try:
        return datetime.strptime(value, BRAZILIAN_DATE_FORMAT).date()
    except ValueError as exc:
        raise ValueError(
            f"Data inválida: {value!r}. Use o formato dd/mm/aaaa."
        ) from exc


def haversine_km(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
) -> float:
    """Calcula a distância em quilômetros entre duas coordenadas.

    Args:
        latitude_a: Latitude do ponto inicial.
        longitude_a: Longitude do ponto inicial.
        latitude_b: Latitude do ponto final.
        longitude_b: Longitude do ponto final.

    Returns:
        Distância aproximada em quilômetros.
    """
    earth_radius_km = 6371.0088

    lat_a = math.radians(latitude_a)
    lon_a = math.radians(longitude_a)
    lat_b = math.radians(latitude_b)
    lon_b = math.radians(longitude_b)

    delta_lat = lat_b - lat_a
    delta_lon = lon_b - lon_a

    hav = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat_a) * math.cos(lat_b) * math.sin(delta_lon / 2) ** 2
    )
    return 2 * earth_radius_km * math.asin(math.sqrt(hav))


def format_duration(value: timedelta | float | int) -> str:
    """Formata uma duração como ``HH:MM``.

    Args:
        value: Timedelta ou quantidade de segundos.

    Returns:
        Duração formatada.
    """
    if isinstance(value, timedelta):
        total_seconds = int(max(value.total_seconds(), 0))
    else:
        total_seconds = int(max(float(value), 0))

    hours, remainder = divmod(total_seconds, 3600)
    minutes = remainder // 60
    return f"{hours:02d}:{minutes:02d}"


def sanitize_filename(value: str) -> str:
    """Gera um nome de arquivo seguro a partir de um texto livre.

    Args:
        value: Texto original.

    Returns:
        Texto normalizado para uso em nomes de arquivo.
    """
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", ascii_text).strip("_")
    return safe or "rota"


def distancia_haversine_metros(
    lat1: float, lon1: float,
    lat2: float, lon2: float,
) -> float:
    """Calcula a distância em metros entre duas coordenadas via haversine.

    Args:
        lat1, lon1: Coordenadas do ponto A.
        lat2, lon2: Coordenadas do ponto B.

    Returns:
        Distância em metros.
    """
    R = 6_371_008.8
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return 2 * R * math.asin(math.sqrt(a))


def ensure_directory(path: str | Path) -> Path:
    """Cria uma pasta quando ela ainda não existe.

    Args:
        path: Caminho da pasta.

    Returns:
        Caminho como ``Path``.
    """
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory
