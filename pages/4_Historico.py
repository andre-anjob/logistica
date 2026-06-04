"""Comparativo histórico entre períodos."""

from __future__ import annotations

from datetime import timedelta

import streamlit as st
from utils.styles import aplicar_estilos

from components.charts import grafico_comparativo
from components.kpi_cards import renderizar_kpis
from config import ROUTE_DATE_COLUMN
from core.analytics import calcular_kpis_frota, calcular_resumo_diario
from core.cache_manager import dados_disponiveis
from core.database import (
    consultar_dados,
    consultar_periodo,
    consultar_veiculos,
    inicializar_banco,
)


def main() -> None:
    """Renderiza o comparativo de períodos."""
    st.set_page_config(layout="wide", page_title="Histórico", page_icon="📈")
    aplicar_estilos()
    st.title("Histórico Comparativo")

    inicializar_banco()
    if not dados_disponiveis():
        st.warning("Nenhum dado carregado. Acesse **Upload de Dados** para começar.")
        st.page_link("pages/5_Upload_de_Dados.py", label="Ir para Upload de Dados")
        st.stop()

    try:
        periodo_banco = consultar_periodo()
        if periodo_banco is None:
            st.warning("Nenhum dado disponível.")
            st.stop()

        min_date, max_date = periodo_banco
        default_a_end = max(min_date, max_date - timedelta(days=7))
        default_a_start = max(min_date, default_a_end - timedelta(days=6))
        default_b_start = max(min_date, max_date - timedelta(days=6))

        col_a, col_b = st.sidebar.columns(2)
        with col_a:
            periodo_a = st.date_input(
                "Período A",
                value=st.session_state.get(
                    "historico_periodo_a",
                    (default_a_start, default_a_end),
                ),
                min_value=min_date,
                max_value=max_date,
                key="historico_periodo_a",
            )
        with col_b:
            periodo_b = st.date_input(
                "Período B",
                value=st.session_state.get(
                    "historico_periodo_b",
                    (default_b_start, max_date),
                ),
                min_value=min_date,
                max_value=max_date,
                key="historico_periodo_b",
            )

        vehicles = consultar_veiculos()
        selected_vehicles = st.sidebar.multiselect(
            "Veículos",
            options=vehicles,
            default=st.session_state.get("historico_veiculos", []),
            key="historico_veiculos",
        )
        limite = st.sidebar.slider(
            "Limite de velocidade (km/h)",
            min_value=40,
            max_value=140,
            value=80,
            step=5,
            key="historico_limite_velocidade",
        )

        inicio_a, fim_a = _normalizar_periodo(periodo_a, min_date, max_date)
        inicio_b, fim_b = _normalizar_periodo(periodo_b, min_date, max_date)
        veiculos_param = selected_vehicles or None

        dados_a = consultar_dados(inicio_a, fim_a, veiculos=veiculos_param)
        dados_b = consultar_dados(inicio_b, fim_b, veiculos=veiculos_param)

        kpis_a = calcular_kpis_frota(dados_a, float(limite))
        kpis_b = calcular_kpis_frota(dados_b, float(limite))
        resumo_a = calcular_resumo_diario(dados_a, float(limite))
        resumo_b = calcular_resumo_diario(dados_b, float(limite))

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Período A")
            renderizar_kpis(kpis_a, colunas=3)
        with col2:
            st.subheader("Período B")
            renderizar_kpis(kpis_b, colunas=3)

        st.subheader("Variação do período B contra A")
        d1, d2, d3, d4 = st.columns(4)
        d1.metric("Km total", f"{kpis_b['total_km']:.1f} km", _delta(kpis_a["total_km"], kpis_b["total_km"]))
        d2.metric(
            "Velocidade média",
            f"{kpis_b['velocidade_media']:.1f} km/h",
            _delta(kpis_a["velocidade_media"], kpis_b["velocidade_media"]),
        )
        d3.metric("Alertas", int(kpis_b["total_alertas"]), _delta(kpis_a["total_alertas"], kpis_b["total_alertas"]))
        d4.metric("Paradas", int(kpis_b["total_paradas"]), _delta(kpis_a["total_paradas"], kpis_b["total_paradas"]))

        label_a = f"{inicio_a:%d/%m/%Y} a {fim_a:%d/%m/%Y}"
        label_b = f"{inicio_b:%d/%m/%Y} a {fim_b:%d/%m/%Y}"
        st.plotly_chart(
            grafico_comparativo(resumo_a, resumo_b, label_a, label_b), use_container_width=True,
        )
    except Exception as exc:
        st.error(f"Não foi possível renderizar o histórico: {exc}")


def _normalizar_periodo(periodo: object, min_date: object, max_date: object) -> tuple:
    if isinstance(periodo, tuple) and len(periodo) == 2:
        return periodo[0], periodo[1]
    if isinstance(periodo, list) and len(periodo) == 2:
        return periodo[0], periodo[1]
    return min_date, max_date


def _delta(valor_a: float, valor_b: float) -> str:
    if float(valor_a) == 0:
        return "0,0%"
    variacao = (float(valor_b) - float(valor_a)) / abs(float(valor_a)) * 100
    return f"{variacao:+.1f}%".replace(".", ",")


main()



