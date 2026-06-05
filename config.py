"""Configurações globais do sistema de rastreamento de frota."""

from __future__ import annotations

from pathlib import Path

EXPECTED_COLUMNS: list[str] = [
    "Veículo",
    "Placa",
    "Organização",
    "Data da Coordenada",
    "Data da Gravação",
    "Velocidade",
    "Ignição",
    "Serial",
    "Posição",
]

DATE_COLUMNS: list[str] = ["Data da Coordenada", "Data da Gravação"]

BRAZILIAN_DATETIME_FORMAT = "%d/%m/%Y %H:%M:%S"
BRAZILIAN_DATE_FORMAT = "%d/%m/%Y"

DEFAULT_OUTPUT_DIR = Path("output")
DEFAULT_SPEED_LIMIT_KMH = 80.0
DEFAULT_STOP_MINUTES = 5

LATITUDE_COLUMN = "latitude"
LONGITUDE_COLUMN = "longitude"
ROUTE_DATE_COLUMN = "data_rota"
STOP_ID_COLUMN = "parada_id"
IS_STOP_COLUMN = "em_parada"

SPEED_BANDS = [
    (0.0, 40.0, "green", "#2ca25f"),
    (40.0, 70.0, "yellow", "#f2c94c"),
    (70.0, float("inf"), "red", "#d73027"),
]

# ── Geocerca da garagem ───────────────────────────────────────────────────────
# Pontos dentro do raio são excluídos do cálculo de tempo parado em rota.
# Altere as coordenadas para a localização real da sua garagem.
GARAGEM_LATITUDE  = -3.8682016092212366
GARAGEM_LONGITUDE = -38.51095701719775
GARAGEM_RAIO_M    = 50.0   # raio em metros
