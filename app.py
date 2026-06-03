"""Home do Portal Logístico em Streamlit."""

from __future__ import annotations

import streamlit as st

from core.cache_manager import (
    carregar_dados_consolidados,
    dados_disponiveis,
    listar_arquivos_carregados,
)


def main() -> None:
    """Renderiza a página inicial do portal."""
    st.set_page_config(layout="wide", page_title="Portal Logístico", page_icon="🚛")
    st.title("Portal Logístico — Rastreamento de Frota")

    _renderizar_acessos()
    st.divider()

    try:
        arquivos = listar_arquivos_carregados()
        if not dados_disponiveis():
            st.warning("Nenhum dado carregado. Acesse **Upload de Dados** para começar.")
            st.page_link("pages/5_Upload_de_Dados.py", label="Ir para Upload de Dados")
            return

        df = carregar_dados_consolidados()
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

        st.subheader("Status dos dados")
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


def _renderizar_acessos() -> None:
    st.subheader("Acesso rápido")
    cards = [
        ("Dashboard Geral", "pages/1_Dashboard.py", "KPIs, gráficos e atividade da frota."),
        ("Mapa de Rotas", "pages/2_Mapa_de_Rotas.py", "Rotas por veículo e dia no mapa."),
        (
            "Análise por Veículo",
            "pages/3_Analise_por_Veiculo.py",
            "Detalhamento individual por período.",
        ),
        ("Histórico", "pages/4_Historico.py", "Comparação entre períodos."),
        ("Upload de Dados", "pages/5_Upload_de_Dados.py", "Enviar e gerenciar CSVs."),
    ]

    columns = st.columns(len(cards))
    for column, (title, target, caption) in zip(columns, cards):
        with column:
            st.page_link(target, label=title)
            st.caption(caption)


if __name__ == "__main__":
    main()
