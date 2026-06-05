"""Home do Portal Logístico — dark theme."""

from __future__ import annotations

import streamlit as st
from utils.styles import aplicar_estilos

from core.cache_manager import (
    carregar_dados_consolidados,
    dados_disponiveis,
    listar_arquivos_carregados,
)


def main() -> None:
    """Renderiza a página inicial do portal."""
    st.set_page_config(layout="wide", page_title="Portal Logístico", page_icon="🚛")
    aplicar_estilos()

    # ── Header ────────────────────────────────────────────────────
    st.markdown("""
    <div class="dash-header">
        <div class="dash-header-left">
            <div class="eyebrow">▸ Anjob Assessoria · Rastreamento de Frota</div>
            <h1>Portal <span>Logístico</span></h1>
        </div>
        <div class="dash-header-right">
            <div class="status-pill">● SISTEMA ATIVO</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Acesso rápido ─────────────────────────────────────────────
    st.markdown("<div class='section-label'>Acesso rápido</div>", unsafe_allow_html=True)

    cards = [
        ("🚛 Dashboard Geral", "pages/1_Dashboard.py", "KPIs, gráficos e atividade da frota.", "green"),
        ("🗺 Mapa de Rotas", "pages/2_Mapa_de_Rotas.py", "Rotas por veículo e dia no mapa.", "blue"),
        ("🚗 Análise por Veículo", "pages/3_Analise_por_Veiculo.py", "Detalhamento individual por período.", "accent-green"),
        ("📈 Histórico", "pages/4_Historico.py", "Comparação entre períodos.", "blue"),
        ("⬆ Upload de Dados", "pages/5_Upload_de_Dados.py", "Enviar e gerenciar CSVs.", "orange"),
    ]

    cols = st.columns(len(cards))
    for col, (title, target, caption, _accent) in zip(cols, cards):
        with col:
            st.markdown(f"""
            <div class="kpi-card accent-{_accent.replace('accent-', '')}" style="cursor:pointer;padding:16px 18px">
                <div class="kpi-label" style="margin-bottom:6px">{caption}</div>
                <div style="font-family:'Syne',sans-serif;font-size:14px;font-weight:700;color:#e8eaf0">{title}</div>
            </div>
            """, unsafe_allow_html=True)
            st.page_link(target, label="Acessar →")

    st.divider()

    # ── Status dos dados ──────────────────────────────────────────
    try:
        arquivos = listar_arquivos_carregados()
        if not dados_disponiveis():
            st.warning("Nenhum dado carregado. Acesse **Upload de Dados** para começar.")
            st.page_link("pages/5_Upload_de_Dados.py", label="Ir para Upload de Dados")
            return

        df = carregar_dados_consolidados()

        # Métricas de status
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Arquivos CSV", len([a for a in arquivos if a["valido"]]))
        with col2:
            st.metric("Veículos únicos", int(df["Veículo"].nunique()))
        with col3:
            st.metric("Registros carregados", f"{len(df):,}".replace(",", "."))
        with col4:
            periodo = f"{df['data_rota'].min():%d/%m/%Y} → {df['data_rota'].max():%d/%m/%Y}"
            st.metric("Período disponível", periodo)

        st.markdown("<div class='section-label'>Status dos arquivos carregados</div>", unsafe_allow_html=True)
        st.dataframe(
            [
                {
                    "Arquivo": item["nome"],
                    "Tamanho (KB)": item["tamanho_kb"],
                    "Início": item["periodo_inicio"],
                    "Fim": item["periodo_fim"],
                    "Veículos": item["veiculos"],
                    "Registros": item["total_registros"],
                }
                for item in arquivos
            ],
            use_container_width=True,
            hide_index=True,
        )
    except Exception as exc:
        st.error(f"Não foi possível carregar o status do portal: {exc}")


main()
