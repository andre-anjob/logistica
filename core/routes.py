"""Agrupamento e análise de rotas por veículo e dia."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import timedelta
from typing import Any

import numpy as np
import pandas as pd

from config import LATITUDE_COLUMN, LONGITUDE_COLUMN, ROUTE_DATE_COLUMN
from utils.helpers import haversine_km


def iter_vehicle_day_routes(df: pd.DataFrame) -> Iterator[tuple[tuple[str, str, object], pd.DataFrame]]:
    """Itera por rotas agrupadas por veículo, placa e dia.

    Args:
        df: DataFrame de rastreamento.

    Yields:
        Tuplas com chave ``(veículo, placa, data)`` e DataFrame da rota.
    """
    for key, group in df.groupby(["Veículo", "Placa", ROUTE_DATE_COLUMN], sort=True, observed=True):
        yield key, group.sort_values("Data da Coordenada").reset_index(drop=True).copy()


def add_segment_distances(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula a distância de cada trecho entre coordenadas consecutivas.

    Args:
        df: DataFrame de uma rota.

    Returns:
        DataFrame com a coluna ``distancia_trecho_km``.
    """
    route = df.sort_values("Data da Coordenada").reset_index(drop=True).copy()
    if len(route) < 2:
        route["distancia_trecho_km"] = 0.0
        return route

    R = 6371.0088
    lat1 = np.radians(route[LATITUDE_COLUMN].values)
    lon1 = np.radians(route[LONGITUDE_COLUMN].values)
    lat2 = np.radians(
        route[LATITUDE_COLUMN].shift(1, fill_value=route[LATITUDE_COLUMN].iloc[0]).values
    )
    lon2 = np.radians(
        route[LONGITUDE_COLUMN].shift(1, fill_value=route[LONGITUDE_COLUMN].iloc[0]).values
    )

    dlat = lat1 - lat2
    dlon = lon1 - lon2
    a = np.sin(dlat / 2) ** 2 + np.cos(lat2) * np.cos(lat1) * np.sin(dlon / 2) ** 2
    dist = 2 * R * np.arcsin(np.sqrt(a))
    dist[0] = 0.0
    route["distancia_trecho_km"] = dist
    return route


def analyze_route(route_df: pd.DataFrame, stops_df: pd.DataFrame) -> dict[str, Any]:
    """Calcula totais de rota para um veículo em um dia.

    Args:
        route_df: DataFrame da rota.
        stops_df: DataFrame de paradas da mesma rota.

    Returns:
        Dicionário com distância, horários e tempos consolidados.
    """
    route = add_segment_distances(route_df)
    start_time = route["Data da Coordenada"].min()
    end_time = route["Data da Coordenada"].max()
    total_duration = max(end_time - start_time, timedelta())

    stopped_seconds = 0.0
    if not stops_df.empty:
        stopped_seconds = float(stops_df["duracao_minutos"].fillna(0.0).sum() * 60)

    moving_seconds = max(total_duration.total_seconds() - stopped_seconds, 0.0)

    return {
        "Veículo": route["Veículo"].iloc[0],
        "Placa": route["Placa"].iloc[0],
        ROUTE_DATE_COLUMN: route[ROUTE_DATE_COLUMN].iloc[0],
        "inicio": start_time,
        "fim": end_time,
        "distancia_km": float(route["distancia_trecho_km"].sum()),
        "tempo_total": total_duration,
        "tempo_movimento_segundos": moving_seconds,
        "tempo_parado_segundos": stopped_seconds,
        "registros": int(len(route)),
        "rota": route,
    }


def filter_stops_for_route(
    stops_df: pd.DataFrame,
    vehicle: str,
    plate: str,
    route_date: object,
) -> pd.DataFrame:
    """Seleciona paradas pertencentes a uma rota.

    Args:
        stops_df: DataFrame com paradas classificadas.
        vehicle: Nome do veículo.
        plate: Placa do veículo.
        route_date: Data da rota.

    Returns:
        DataFrame de paradas da rota.
    """
    if stops_df.empty:
        return stops_df.copy()

    mask = (
        (stops_df["Veículo"] == vehicle)
        & (stops_df["Placa"] == plate)
        & (stops_df[ROUTE_DATE_COLUMN] == route_date)
    )
    return stops_df.loc[mask].copy()
