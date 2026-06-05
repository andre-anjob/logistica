"""Cards de KPIs para o portal — dark theme."""

from __future__ import annotations

import streamlit as st


def renderizar_kpis(kpis: dict, colunas: int = 4) -> None:
    """Exibe KPIs em cards dark com HTML customizado.

    Args:
        kpis: Dicionário de KPIs.
        colunas: Quantidade de colunas por linha.
    """
    items = [
        ("km total", f"{float(kpis.get('total_km', 0)):.1f}", "km percorridos", "green", "green"),
        ("vel. média", f"{float(kpis.get('velocidade_media', 0)):.1f}", "km/h · em movimento", "blue", "blue"),
        ("alertas", f"{int(kpis.get('total_alertas', 0))}", "excesso de velocidade", "orange", "orange"),
        ("veículos", f"{int(kpis.get('veiculos_ativos', 0))}", "ativos no período", "green", "green"),
        ("ign. ligada", f"{float(kpis.get('horas_ignicao_ligada', 0)):.1f}", "horas com motor ligado", "blue", "blue"),
        ("paradas", f"{int(kpis.get('total_paradas', 0))}", "total no período", "muted", "white"),
    ]

    for start in range(0, len(items), colunas):
        cols = st.columns(colunas)
        for col, (label, value, sub, accent, color) in zip(cols, items[start : start + colunas]):
            with col:
                st.markdown(
                    f"""<div class="kpi-card accent-{accent}">
                        <div class="kpi-label">{label}</div>
                        <div class="kpi-value {color}">{value}</div>
                        <div class="kpi-sub">{sub}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )


def kpi_card_html(label: str, value: str, sub: str, accent: str = "green", color: str = "green") -> str:
    """Retorna HTML de um único card de KPI."""
    return f"""<div class="kpi-card accent-{accent}">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value {color}">{value}</div>
        <div class="kpi-sub">{sub}</div>
    </div>"""
