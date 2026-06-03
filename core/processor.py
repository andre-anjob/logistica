"""Processamento, filtragem e identificação de paradas."""

from __future__ import annotations

from datetime import date

import pandas as pd

from config import (
    DEFAULT_STOP_MINUTES,
    IS_STOP_COLUMN,
    LATITUDE_COLUMN,
    LONGITUDE_COLUMN,
    ROUTE_DATE_COLUMN,
    STOP_ID_COLUMN,
)


def filter_by_vehicle(df: pd.DataFrame, vehicle_or_plate: str | None) -> pd.DataFrame:
    """Filtra registros por nome do veículo ou placa.

    Args:
        df: DataFrame de rastreamento.
        vehicle_or_plate: Nome do veículo ou placa. Quando None, não filtra.

    Returns:
        DataFrame filtrado.
    """
    if not vehicle_or_plate:
        return df.copy()

    needle = vehicle_or_plate.strip().casefold()
    vehicle_match = df["Veículo"].astype(str).str.casefold().str.contains(
        needle,
        na=False,
        regex=False,
    )
    plate_match = df["Placa"].astype(str).str.casefold().str.contains(
        needle,
        na=False,
        regex=False,
    )
    return df.loc[vehicle_match | plate_match].copy()


def filter_by_date(df: pd.DataFrame, target_date: date) -> pd.DataFrame:
    """Filtra registros de uma data específica.

    Args:
        df: DataFrame de rastreamento.
        target_date: Data desejada.

    Returns:
        DataFrame filtrado.
    """
    return df.loc[df[ROUTE_DATE_COLUMN] == target_date].copy()


def filter_by_date_range(
    df: pd.DataFrame,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    """Filtra registros dentro de um intervalo de datas fechado.

    Args:
        df: DataFrame de rastreamento.
        start_date: Data inicial.
        end_date: Data final.

    Returns:
        DataFrame filtrado.
    """
    mask = (df[ROUTE_DATE_COLUMN] >= start_date) & (df[ROUTE_DATE_COLUMN] <= end_date)
    return df.loc[mask].copy()


def sort_records(df: pd.DataFrame) -> pd.DataFrame:
    """Ordena registros por veículo, placa e data da coordenada.

    Args:
        df: DataFrame de rastreamento.

    Returns:
        DataFrame ordenado.
    """
    return (
        df.sort_values(["Veículo", "Placa", "Data da Coordenada"], kind="mergesort")
        .reset_index(drop=True)
        .copy()
    )


def classify_stops(
    df: pd.DataFrame,
    min_stop_minutes: int = DEFAULT_STOP_MINUTES,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Classifica paradas prolongadas e calcula sua duração.

    Uma parada é uma sequência de pontos com ignição desligada ou velocidade zero
    cuja duração total é maior ou igual ao limite configurado.

    Args:
        df: DataFrame de rastreamento ordenável.
        min_stop_minutes: Duração mínima para considerar uma parada.

    Returns:
        Tupla com DataFrame enriquecido e DataFrame de paradas.
    """
    if df.empty:
        enriched = df.copy()
        enriched[IS_STOP_COLUMN] = False
        enriched[STOP_ID_COLUMN] = pd.NA
        return enriched, _empty_stops_dataframe()

    ordered = sort_records(df)
    ordered[IS_STOP_COLUMN] = False
    ordered[STOP_ID_COLUMN] = pd.NA

    stops: list[dict[str, object]] = []
    next_stop_id = 1

    group_columns = ["Veículo", "Placa", ROUTE_DATE_COLUMN]
    for _, group in ordered.groupby(group_columns, sort=False, observed=True):
        candidate = _is_stop_candidate(group)
        sequence_id = candidate.ne(candidate.shift(fill_value=False)).cumsum()

        for _, sequence in group.loc[candidate].groupby(sequence_id[candidate], sort=False):
            start_time = sequence["Data da Coordenada"].min()
            end_time = sequence["Data da Coordenada"].max()
            duration_minutes = max((end_time - start_time).total_seconds() / 60, 0.0)

            if duration_minutes < min_stop_minutes:
                continue

            original_indexes = sequence.index
            ordered.loc[original_indexes, IS_STOP_COLUMN] = True
            ordered.loc[original_indexes, STOP_ID_COLUMN] = next_stop_id

            stops.append(
                {
                    "parada_id": next_stop_id,
                    "Veículo": sequence["Veículo"].iloc[0],
                    "Placa": sequence["Placa"].iloc[0],
                    ROUTE_DATE_COLUMN: sequence[ROUTE_DATE_COLUMN].iloc[0],
                    "inicio": start_time,
                    "fim": end_time,
                    "duracao_minutos": duration_minutes,
                    LATITUDE_COLUMN: float(sequence[LATITUDE_COLUMN].median()),
                    LONGITUDE_COLUMN: float(sequence[LONGITUDE_COLUMN].median()),
                    "registros": int(len(sequence)),
                }
            )
            next_stop_id += 1

    stops_df = pd.DataFrame(stops)
    if stops_df.empty:
        stops_df = _empty_stops_dataframe()

    return ordered.reset_index(drop=True), stops_df


def _is_stop_candidate(group: pd.DataFrame) -> pd.Series:
    ignition_off = group["Ignição"].astype(str).str.strip().str.casefold() == "desligada"
    speed_zero = group["Velocidade"].fillna(0.0).astype(float) <= 0.0
    return ignition_off | speed_zero


def _empty_stops_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "parada_id",
            "Veículo",
            "Placa",
            ROUTE_DATE_COLUMN,
            "inicio",
            "fim",
            "duracao_minutos",
            LATITUDE_COLUMN,
            LONGITUDE_COLUMN,
            "registros",
        ]
    )
