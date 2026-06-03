"""Filtros reutilizáveis da barra lateral do portal."""

from __future__ import annotations

from datetime import timedelta

import pandas as pd
import streamlit as st

from config import ROUTE_DATE_COLUMN


def renderizar_filtros(df: pd.DataFrame) -> dict:
    """Renderiza filtros globais na sidebar.

    Args:
        df: DataFrame de rastreamento disponível.

    Returns:
        Dicionário com período, veículos e organizações selecionados.
    """
    st.sidebar.header("Filtros")

    min_date = df[ROUTE_DATE_COLUMN].min()
    max_date = df[ROUTE_DATE_COLUMN].max()
    default_start = max(min_date, max_date - timedelta(days=6))

    periodo = st.sidebar.date_input(
        "Período",
        value=st.session_state.get("filtro_periodo", (default_start, max_date)),
        min_value=min_date,
        max_value=max_date,
        key="filtro_periodo",
    )
    data_inicio, data_fim = _normalizar_periodo(periodo, default_start, max_date)

    veiculos = sorted(df["Veículo"].dropna().astype(str).unique().tolist())
    organizacoes = sorted(df["Organização"].dropna().astype(str).unique().tolist())

    veiculos_selecionados = st.sidebar.multiselect(
        "Veículos",
        options=veiculos,
        default=st.session_state.get("filtro_veiculos", []),
        key="filtro_veiculos",
    )
    organizacoes_selecionadas = st.sidebar.multiselect(
        "Organização",
        options=organizacoes,
        default=st.session_state.get("filtro_organizacoes", []),
        key="filtro_organizacoes",
    )

    return {
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "veiculos": veiculos_selecionados,
        "organizacoes": organizacoes_selecionadas,
    }


def aplicar_filtros(df: pd.DataFrame, filtros: dict) -> pd.DataFrame:
    """Aplica os filtros selecionados ao DataFrame.

    Args:
        df: DataFrame original.
        filtros: Dicionário retornado por ``renderizar_filtros``.

    Returns:
        DataFrame filtrado.
    """
    if df.empty:
        return df.copy()

    filtered = df.copy()
    filtered = filtered.loc[
        (filtered[ROUTE_DATE_COLUMN] >= filtros["data_inicio"])
        & (filtered[ROUTE_DATE_COLUMN] <= filtros["data_fim"])
    ]

    if filtros.get("veiculos"):
        filtered = filtered.loc[filtered["Veículo"].astype(str).isin(filtros["veiculos"])]

    if filtros.get("organizacoes"):
        filtered = filtered.loc[
            filtered["Organização"].astype(str).isin(filtros["organizacoes"])
        ]

    return filtered.copy()


def _normalizar_periodo(periodo: object, default_start: object, max_date: object) -> tuple:
    if isinstance(periodo, tuple) and len(periodo) == 2:
        return periodo[0], periodo[1]
    if isinstance(periodo, list) and len(periodo) == 2:
        return periodo[0], periodo[1]
    return default_start, max_date
