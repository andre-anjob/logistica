"""Análise individual por veículo."""

from __future__ import annotations

from datetime import timedelta
from io import BytesIO

import pandas as pd
import plotly.express as px
import streamlit as st

from components.charts import grafico_evolucao_diaria
from components.kpi_cards import renderizar_kpis
from config import ROUTE_DATE_COLUMN
from core.analytics import calcular_kpis_veiculo, calcular_resumo_diario
from core.cache_manager import dados_disponiveis
from core.database import (
    consultar_dados,
    consultar_periodo,
    consultar_veiculos,
    inicializar_banco,
)


def main() -> None:
    """Renderiza análise individual de um veículo."""
    st.set_page_config(layout="wide", page_title="Análise por Veículo", page_icon="🚗")
    st.title("Análise por Veículo")

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
        vehicles = consultar_veiculos()
        selected_vehicle = st.sidebar.selectbox(
            "Veículo",
            options=vehicles,
            key="analise_veiculo",
        )

        default_start = max(min_date, max_date - timedelta(days=6))
        periodo = st.sidebar.date_input(
            "Período",
            value=st.session_state.get("analise_periodo", (default_start, max_date)),
            min_value=min_date,
            max_value=max_date,
            key="analise_periodo",
        )
        data_inicio, data_fim = _normalizar_periodo(periodo, default_start, max_date)
        limite = st.sidebar.slider(
            "Limite de velocidade (km/h)",
            min_value=40,
            max_value=140,
            value=80,
            step=5,
            key="analise_limite_velocidade",
        )

        filtrado = consultar_dados(
            data_inicio, data_fim, veiculos=[selected_vehicle]
        )

        if filtrado.empty:
            st.warning("Nenhum dado encontrado para o veículo e período selecionados.")
            st.stop()

        kpis = calcular_kpis_veiculo(filtrado, selected_vehicle, float(limite))
        resumo = calcular_resumo_diario(filtrado, float(limite))

        renderizar_kpis(kpis)
        st.plotly_chart(grafico_evolucao_diaria(resumo), width="stretch")

        col1, col2 = st.columns(2)
        with col1:
            fig_vel = px.line(
                resumo,
                x=ROUTE_DATE_COLUMN,
                y="velocidade_maxima",
                markers=True,
                title="Velocidade máxima por dia",
            )
            st.plotly_chart(fig_vel, width="stretch")
        with col2:
            fig_paradas = px.bar(
                resumo,
                x=ROUTE_DATE_COLUMN,
                y="quantidade_paradas",
                title="Quantidade de paradas por dia",
            )
            st.plotly_chart(fig_paradas, width="stretch")

        tabela = _formatar_tabela(resumo)
        st.dataframe(tabela, width="stretch", hide_index=True)
        st.download_button(
            "Baixar tabela em Excel",
            data=_gerar_excel(tabela),
            file_name=f"analise_{selected_vehicle}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except Exception as exc:
        st.error(f"Não foi possível renderizar a análise do veículo: {exc}")


def _formatar_tabela(resumo: pd.DataFrame) -> pd.DataFrame:
    tabela = resumo.copy()
    tabela["Data"] = pd.to_datetime(tabela[ROUTE_DATE_COLUMN]).dt.strftime("%d/%m/%Y")
    tabela["Início"] = pd.to_datetime(tabela["inicio"]).dt.strftime("%H:%M")
    tabela["Fim"] = pd.to_datetime(tabela["fim"]).dt.strftime("%H:%M")
    tabela = tabela.rename(
        columns={
            "km_total": "Km Total",
            "velocidade_maxima": "Vel. Máx",
            "velocidade_media": "Vel. Média",
            "alertas_velocidade": "Alertas",
            "quantidade_paradas": "Paradas",
        }
    )
    return tabela[
        ["Data", "Km Total", "Vel. Máx", "Vel. Média", "Alertas", "Paradas", "Início", "Fim"]
    ]


def _gerar_excel(tabela: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        tabela.to_excel(writer, index=False, sheet_name="Análise")
    return buffer.getvalue()


def _normalizar_periodo(periodo: object, default_start: object, max_date: object) -> tuple:
    if isinstance(periodo, tuple) and len(periodo) == 2:
        return periodo[0], periodo[1]
    if isinstance(periodo, list) and len(periodo) == 2:
        return periodo[0], periodo[1]
    return default_start, max_date


main()

