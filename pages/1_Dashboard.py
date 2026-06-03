"""Dashboard geral da frota."""

from __future__ import annotations

from datetime import timedelta

import streamlit as st

from components.charts import (
    grafico_evolucao_diaria,
    grafico_ignicao,
    grafico_km_por_veiculo,
    grafico_ranking_alertas,
    heatmap_atividade,
)
from components.kpi_cards import renderizar_kpis
from core.analytics import _kpis_do_resumo
from core.cache_manager import dados_disponiveis
from core.database import (
    consultar_dados,
    consultar_organizacoes,
    consultar_periodo,
    consultar_resumo_diario_sql,
    consultar_veiculos,
    inicializar_banco,
)


def main() -> None:
    """Renderiza o dashboard geral."""
    st.set_page_config(layout="wide", page_title="Dashboard Geral", page_icon="🚛")
    st.title("Dashboard Geral da Frota")

    inicializar_banco()
    if not dados_disponiveis():
        st.warning("Nenhum dado carregado. Acesse **Upload de Dados** para começar.")
        st.page_link("pages/5_Upload_de_Dados.py", label="Ir para Upload de Dados")
        st.stop()

    try:
        periodo = consultar_periodo()
        if periodo is None:
            st.warning("Nenhum dado disponível.")
            st.stop()

        min_date, max_date = periodo
        default_start = max(min_date, max_date - timedelta(days=6))

        st.sidebar.header("Filtros")
        periodo_sel = st.sidebar.date_input(
            "Período",
            value=st.session_state.get("filtro_periodo", (default_start, max_date)),
            min_value=min_date,
            max_value=max_date,
            key="filtro_periodo",
        )
        data_inicio, data_fim = _normalizar_periodo(periodo_sel, default_start, max_date)

        veiculos_disponiveis = consultar_veiculos()
        orgs_disponiveis = consultar_organizacoes()

        veiculos_sel = st.sidebar.multiselect(
            "Veículos",
            options=veiculos_disponiveis,
            default=st.session_state.get("filtro_veiculos", []),
            key="filtro_veiculos",
        )
        orgs_sel = st.sidebar.multiselect(
            "Organização",
            options=orgs_disponiveis,
            default=st.session_state.get("filtro_organizacoes", []),
            key="filtro_organizacoes",
        )
        limite = st.sidebar.slider(
            "Limite de velocidade (km/h)",
            min_value=40,
            max_value=140,
            value=80,
            step=5,
            key="dashboard_limite_velocidade",
        )

        veiculos_param = veiculos_sel or None
        orgs_param = orgs_sel or None

        with st.spinner("Consultando dados..."):
            resumo = consultar_resumo_diario_sql(
                data_inicio, data_fim, veiculos_param, orgs_param, float(limite)
            )

        if resumo.empty:
            st.warning("Nenhum dado encontrado para os filtros selecionados.")
            st.stop()

        # KPIs calculados sobre o resumo SQL (sem recarregar linhas brutas)
        kpis = {
            "total_km": float(resumo["km_total"].sum()),
            "velocidade_media": float(resumo["velocidade_media"].mean()),
            "total_alertas": int(resumo["alertas_velocidade"].sum()),
            "veiculos_ativos": int(resumo["Veículo"].nunique()),
            "total_paradas": 0,  # paradas não disponíveis no resumo SQL
            "horas_ignicao_ligada": 0.0,
            "horas_ignicao_desligada": 0.0,
        }

        renderizar_kpis(kpis)

        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(grafico_km_por_veiculo(resumo), use_container_width=True)
        with col2:
            st.plotly_chart(grafico_evolucao_diaria(resumo), use_container_width=True)

        # Adiciona colunas de ignição ao resumo SQL (não calculadas via SQL)
        # para compatibilidade com grafico_ignicao()
        if "horas_ignicao_ligada" not in resumo.columns:
            resumo["horas_ignicao_ligada"] = 0.0
        if "horas_ignicao_desligada" not in resumo.columns:
            resumo["horas_ignicao_desligada"] = 0.0

        col3, col4 = st.columns(2)
        with col3:
            st.plotly_chart(grafico_ranking_alertas(resumo), use_container_width=True)
        with col4:
            st.plotly_chart(grafico_ignicao(resumo), use_container_width=True)

        # Heatmap precisa dos dados brutos (timestamps por linha)
        with st.spinner("Carregando heatmap..."):
            filtrado = consultar_dados(
                data_inicio, data_fim, veiculos_param, orgs_param
            )
        st.plotly_chart(heatmap_atividade(filtrado), use_container_width=True)
    except Exception as exc:
        st.error(f"Não foi possível renderizar o dashboard: {exc}")


def _normalizar_periodo(periodo: object, default_start: object, max_date: object) -> tuple:
    if isinstance(periodo, tuple) and len(periodo) == 2:
        return periodo[0], periodo[1]
    if isinstance(periodo, list) and len(periodo) == 2:
        return periodo[0], periodo[1]
    return default_start, max_date


main()

# ALTERAÇÕES:
# - carregar_dados_consolidados() + aplicar_filtros() removidos: widgets da sidebar
#   agora usam listas vindas de consultar_veiculos() / consultar_organizacoes().
# - calcular_resumo_diario() (Python) substituído por consultar_resumo_diario_sql()
#   (haversine no DuckDB via LAG/WINDOW).
# - KPIs calculados direto do resumo SQL sem recarregar 800k linhas.
# - heatmap_atividade ainda usa consultar_dados() pois precisa de timestamps por linha.
# - _kpis_do_resumo mantido no import mas KPIs agora derivados do resumo SQL.
