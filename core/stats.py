"""Cálculo de estatísticas operacionais das rotas."""

from __future__ import annotations

import pandas as pd


def calculate_route_stats(
    route_df: pd.DataFrame,
    stops_df: pd.DataFrame,
    speed_limit: float,
) -> dict[str, float | int]:
    """Calcula estatísticas de velocidade, paradas e ignição.

    Args:
        route_df: DataFrame da rota.
        stops_df: DataFrame de paradas da rota.
        speed_limit: Limite para alerta de excesso de velocidade, em km/h.

    Returns:
        Dicionário com métricas consolidadas.
    """
    velocidade = route_df["Velocidade"].astype(float)
    moving = route_df.loc[velocidade > 0].copy()

    speed_average = float(moving["Velocidade"].mean()) if not moving.empty else 0.0
    speed_max = float(moving["Velocidade"].max()) if not moving.empty else 0.0
    speed_min = float(moving["Velocidade"].min()) if not moving.empty else 0.0

    overspeed_alerts = int((velocidade > speed_limit).sum())
    stop_count = int(len(stops_df))
    average_stop_minutes = (
        float(stops_df["duracao_minutos"].mean()) if not stops_df.empty else 0.0
    )
    ignition = calculate_ignition_percentages(route_df)

    return {
        "velocidade_media": speed_average,
        "velocidade_maxima": speed_max,
        "velocidade_minima": speed_min,
        "alertas_velocidade": overspeed_alerts,
        "quantidade_paradas": stop_count,
        "duracao_media_parada_minutos": average_stop_minutes,
        "percentual_ignicao_ligada": ignition["ligada"],
        "percentual_ignicao_desligada": ignition["desligada"],
    }


def calculate_ignition_percentages(route_df: pd.DataFrame) -> dict[str, float]:
    """Calcula percentual de tempo com ignição ligada e desligada.

    Args:
        route_df: DataFrame da rota.

    Returns:
        Dicionário com percentuais ``ligada`` e ``desligada``.
    """
    if route_df.empty:
        return {"ligada": 0.0, "desligada": 0.0}

    route = route_df.sort_values("Data da Coordenada").reset_index(drop=True).copy()
    deltas = (
        route["Data da Coordenada"].shift(-1) - route["Data da Coordenada"]
    ).dt.total_seconds()
    route["delta_segundos"] = deltas.clip(lower=0).fillna(0.0)

    total_seconds = float(route["delta_segundos"].sum())
    normalized_ignition = route["Ignição"].astype(str).str.strip().str.casefold()

    if total_seconds <= 0:
        total_records = max(len(route), 1)
        ligada = float((normalized_ignition == "ligada").sum() / total_records * 100)
        desligada = float((normalized_ignition == "desligada").sum() / total_records * 100)
        return {"ligada": ligada, "desligada": desligada}

    ligada_seconds = float(route.loc[normalized_ignition == "ligada", "delta_segundos"].sum())
    desligada_seconds = float(
        route.loc[normalized_ignition == "desligada", "delta_segundos"].sum()
    )

    return {
        "ligada": ligada_seconds / total_seconds * 100,
        "desligada": desligada_seconds / total_seconds * 100,
    }
