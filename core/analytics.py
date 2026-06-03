"""KPIs agregados para o portal logístico."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from config import DEFAULT_SPEED_LIMIT_KMH, ROUTE_DATE_COLUMN
from core.processor import classify_stops, sort_records
from core.routes import analyze_route, filter_stops_for_route, iter_vehicle_day_routes
from core.stats import calculate_route_stats


@st.cache_data(ttl=300, show_spinner="Calculando resumo diário...")
def calcular_resumo_diario(
    df: pd.DataFrame,
    speed_limit: float = DEFAULT_SPEED_LIMIT_KMH,
) -> pd.DataFrame:
    """Calcula uma linha por veículo, placa e dia.

    Args:
        df: Dados de rastreamento filtrados.
        speed_limit: Limite de velocidade para alertas.

    Returns:
        DataFrame com métricas diárias consolidadas.
    """
    if df.empty:
        return _resumo_vazio()

    enriched, stops = classify_stops(sort_records(df))
    rows: list[dict[str, Any]] = []

    for (vehicle, plate, route_date), route_df in iter_vehicle_day_routes(enriched):
        route_stops = filter_stops_for_route(stops, vehicle, plate, route_date)
        summary = analyze_route(route_df, route_stops)
        stats = calculate_route_stats(route_df, route_stops, speed_limit)
        ignition_hours = _calcular_horas_ignicao(route_df)

        rows.append(
            {
                "Veículo": vehicle,
                "Placa": plate,
                ROUTE_DATE_COLUMN: route_date,
                "km_total": float(summary["distancia_km"]),
                "velocidade_media": float(stats["velocidade_media"]),
                "velocidade_maxima": float(stats["velocidade_maxima"]),
                "alertas_velocidade": int(stats["alertas_velocidade"]),
                "quantidade_paradas": int(stats["quantidade_paradas"]),
                "duracao_total_parado_min": float(
                    summary["tempo_parado_segundos"]
                )
                / 60,
                "inicio": summary["inicio"],
                "fim": summary["fim"],
                "horas_ignicao_ligada": ignition_hours["ligada"],
                "horas_ignicao_desligada": ignition_hours["desligada"],
            }
        )

    if not rows:
        return _resumo_vazio()

    return pd.DataFrame(rows)


def calcular_kpis_frota(df: pd.DataFrame, speed_limit: float) -> dict:
    """Calcula KPIs globais do período filtrado.

    Args:
        df: DataFrame de rastreamento.
        speed_limit: Limite de velocidade para alertas.

    Returns:
        Dicionário de KPIs da frota.
    """
    if df.empty:
        return _kpis_vazios()

    resumo = calcular_resumo_diario(df, speed_limit)
    return _kpis_do_resumo(resumo, df, speed_limit)


def _kpis_do_resumo(resumo: pd.DataFrame, df: pd.DataFrame, speed_limit: float) -> dict:
    """Constrói o dicionário de KPIs a partir de um resumo já calculado.

    Args:
        resumo: Resultado de ``calcular_resumo_diario``.
        df: DataFrame de rastreamento original (usado para velocidade/ignição).
        speed_limit: Limite de velocidade para alertas.

    Returns:
        Dicionário de KPIs da frota.
    """
    if df.empty:
        return _kpis_vazios()

    moving = df.loc[df["Velocidade"].astype(float) > 0]
    ignicao = _calcular_horas_ignicao(df)

    return {
        "total_km": float(resumo["km_total"].sum()) if not resumo.empty else 0.0,
        "velocidade_media": float(moving["Velocidade"].mean()) if not moving.empty else 0.0,
        "total_alertas": int((df["Velocidade"].astype(float) > speed_limit).sum()),
        "veiculos_ativos": int(df["Veículo"].nunique()),
        "total_paradas": int(resumo["quantidade_paradas"].sum()) if not resumo.empty else 0,
        "horas_ignicao_ligada": ignicao["ligada"],
        "horas_ignicao_desligada": ignicao["desligada"],
    }


def calcular_kpis_veiculo(df: pd.DataFrame, veiculo: str, speed_limit: float) -> dict:
    """Calcula KPIs de um veículo específico.

    Args:
        df: DataFrame de rastreamento.
        veiculo: Nome ou placa do veículo.
        speed_limit: Limite de velocidade para alertas.

    Returns:
        Dicionário de KPIs do veículo.
    """
    if df.empty or not veiculo:
        return _kpis_vazios()

    mask = (df["Veículo"].astype(str) == veiculo) | (df["Placa"].astype(str) == veiculo)
    return calcular_kpis_frota(df.loc[mask].copy(), speed_limit)


def _calcular_horas_ignicao(df: pd.DataFrame) -> dict[str, float]:
    if df.empty:
        return {"ligada": 0.0, "desligada": 0.0}

    total_ligada = 0.0
    total_desligada = 0.0

    for _, group in df.groupby(["Veículo", "Placa", ROUTE_DATE_COLUMN], sort=False, observed=True):
        route = group.sort_values("Data da Coordenada").reset_index(drop=True).copy()
        deltas = (
            route["Data da Coordenada"].shift(-1) - route["Data da Coordenada"]
        ).dt.total_seconds()
        route["delta_segundos"] = deltas.clip(lower=0).fillna(0.0)
        ignition = route["Ignição"].astype(str).str.strip().str.casefold()
        total_ligada += float(route.loc[ignition == "ligada", "delta_segundos"].sum())
        total_desligada += float(
            route.loc[ignition == "desligada", "delta_segundos"].sum()
        )

    return {
        "ligada": total_ligada / 3600,
        "desligada": total_desligada / 3600,
    }


def _kpis_vazios() -> dict:
    return {
        "total_km": 0.0,
        "velocidade_media": 0.0,
        "total_alertas": 0,
        "veiculos_ativos": 0,
        "total_paradas": 0,
        "horas_ignicao_ligada": 0.0,
        "horas_ignicao_desligada": 0.0,
    }


def _resumo_vazio() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "Veículo",
            "Placa",
            ROUTE_DATE_COLUMN,
            "km_total",
            "velocidade_media",
            "velocidade_maxima",
            "alertas_velocidade",
            "quantidade_paradas",
            "duracao_total_parado_min",
            "inicio",
            "fim",
            "horas_ignicao_ligada",
            "horas_ignicao_desligada",
        ]
    )
