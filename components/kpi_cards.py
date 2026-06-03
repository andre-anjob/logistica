"""Cards de KPIs para o portal."""

from __future__ import annotations

import streamlit as st


def renderizar_kpis(kpis: dict, colunas: int = 4) -> None:
    """Exibe KPIs em cards com ``st.metric``.

    Args:
        kpis: Dicionário de KPIs.
        colunas: Quantidade de colunas por linha.
    """
    items = [
        ("🚛 Total km rodados", f"{float(kpis.get('total_km', 0)):.1f} km"),
        ("⚡ Velocidade média", f"{float(kpis.get('velocidade_media', 0)):.1f} km/h"),
        ("🚨 Alertas de velocidade", f"{int(kpis.get('total_alertas', 0))}"),
        ("🚗 Veículos ativos", f"{int(kpis.get('veiculos_ativos', 0))}"),
        ("⏱️ Horas com ignição ligada", f"{float(kpis.get('horas_ignicao_ligada', 0)):.1f} h"),
        ("🅿️ Total de paradas", f"{int(kpis.get('total_paradas', 0))}"),
    ]

    for start in range(0, len(items), colunas):
        columns = st.columns(colunas)
        for column, (label, value) in zip(columns, items[start : start + colunas]):
            with column:
                st.metric(label, value)
