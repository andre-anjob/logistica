"""Dashboard geral da frota — dark theme."""

from __future__ import annotations

from datetime import timedelta

import streamlit as st
from utils.styles import aplicar_estilos

from components.charts import (
    grafico_evolucao_diaria,
    grafico_ignicao,
    grafico_km_por_veiculo,
    grafico_ranking_alertas,
    heatmap_atividade,
)
from components.kpi_cards import renderizar_kpis
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
    aplicar_estilos()

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
            min_value=40, max_value=140, value=80, step=5,
            key="dashboard_limite_velocidade",
        )

        veiculos_param = veiculos_sel or None
        orgs_param = orgs_sel or None

        # ── Header ────────────────────────────────────────────────
        date_label = f"{data_inicio:%d/%m/%Y} → {data_fim:%d/%m/%Y}"
        st.markdown(f"""
        <div class="dash-header">
            <div class="dash-header-left">
                <div class="eyebrow">▸ Portal Logístico · Monitoramento de Frota</div>
                <h1>Dashboard <span>Geral</span></h1>
            </div>
            <div class="dash-header-right">
                <div class="status-pill">● AO VIVO</div><br>
                {date_label}<br>
                Org: {", ".join(orgs_sel) if orgs_sel else "Todas"}
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.spinner("Consultando dados..."):
            resumo = consultar_resumo_diario_sql(
                data_inicio, data_fim, veiculos_param, orgs_param, float(limite)
            )

        if resumo.empty:
            st.warning("Nenhum dado encontrado para os filtros selecionados.")
            st.stop()

        kpis = {
            "total_km": float(resumo["km_total"].sum()),
            "velocidade_media": float(resumo["velocidade_media"].mean()),
            "total_alertas": int(resumo["alertas_velocidade"].sum()),
            "veiculos_ativos": int(resumo["Veículo"].nunique()),
            "total_paradas": 0,
            "horas_ignicao_ligada": 0.0,
            "horas_ignicao_desligada": 0.0,
        }

        # ── KPI cards ─────────────────────────────────────────────
        renderizar_kpis(kpis)
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        # ── Linha 1: km + evolução diária ─────────────────────────
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(grafico_km_por_veiculo(resumo), use_container_width=True)
        with col2:
            st.plotly_chart(grafico_evolucao_diaria(resumo), use_container_width=True)

        # Adiciona colunas de ignição para compatibilidade com grafico_ignicao()
        if "horas_ignicao_ligada" not in resumo.columns:
            resumo["horas_ignicao_ligada"] = 0.0
        if "horas_ignicao_desligada" not in resumo.columns:
            resumo["horas_ignicao_desligada"] = 0.0

        # ── Linha 2: alertas + ignição ────────────────────────────
        col3, col4 = st.columns(2)
        with col3:
            st.plotly_chart(grafico_ranking_alertas(resumo), use_container_width=True)
        with col4:
            st.plotly_chart(grafico_ignicao(resumo), use_container_width=True)

        # ── Heatmap ───────────────────────────────────────────────
        st.markdown("<div class='section-label'>Atividade por hora e dia</div>", unsafe_allow_html=True)
        with st.spinner("Carregando heatmap..."):
            filtrado = consultar_dados(data_inicio, data_fim, veiculos_param, orgs_param)
        st.plotly_chart(heatmap_atividade(filtrado), use_container_width=True)

    except Exception as exc:
        st.error(f"Não foi possível renderizar o dashboard: {exc}")


def _normalizar_periodo(periodo: object, default_start: object, max_date: object) -> tuple:
    if isinstance(periodo, (tuple, list)) and len(periodo) == 2:
        return periodo[0], periodo[1]
    return default_start, max_date


main()
