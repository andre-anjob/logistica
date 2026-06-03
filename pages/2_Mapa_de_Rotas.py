"""Mapa interativo de rotas — renderizado com PyDeck (WebGL)."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pydeck as pdk
import streamlit as st

from config import LATITUDE_COLUMN, LONGITUDE_COLUMN, ROUTE_DATE_COLUMN
from core.cache_manager import dados_disponiveis
from core.database import consultar_dados, consultar_periodo, inicializar_banco
from core.map_builder import (
    _MAP_STYLE,
    build_pydeck_layers,
    build_pydeck_layers_multi,
)
from core.processor import classify_stops, sort_records
from core.report import build_text_report
from core.routes import analyze_route, filter_stops_for_route, iter_vehicle_day_routes
from core.stats import calculate_route_stats

_TOOLTIP = {
    "html": "<b>{label}</b>",
    "style": {
        "backgroundColor": "rgba(0,0,0,0.72)",
        "color": "white",
        "fontSize": "13px",
        "padding": "6px 10px",
        "borderRadius": "4px",
    },
}


def main() -> None:
    """Renderiza a página de mapas."""
    st.set_page_config(layout="wide", page_title="Mapa de Rotas", page_icon="🗺️")
    st.title("Mapa de Rotas")

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
        default_target = date.today() - timedelta(days=1)
        default_day = min(max_date, max(min_date, default_target))

        selected_day = st.sidebar.date_input(
            "Dia",
            value=st.session_state.get("mapa_dia", default_day),
            min_value=min_date,
            max_value=max_date,
            key="mapa_dia",
        )

        # Carrega apenas o dia selecionado via DuckDB — sem trazer 800k linhas
        day_df = consultar_dados(selected_day, selected_day)

        if day_df.empty:
            st.warning("Nenhum dado encontrado para o dia selecionado.")
            st.stop()

        vehicles = sorted(day_df["Veículo"].dropna().astype(str).unique().tolist())
        selected_vehicle = st.sidebar.selectbox(
            "Veículo",
            options=["Todos"] + vehicles,
            key="mapa_veiculo",
        )
        limite = st.sidebar.slider(
            "Limite de velocidade (km/h)",
            min_value=40,
            max_value=140,
            value=80,
            step=5,
            key="mapa_limite_velocidade",
        )
        mostrar_alertas = st.sidebar.toggle(
            "Mostrar alertas de velocidade",
            value=True,
            key="mapa_mostrar_alertas",
        )
        mostrar_paradas = st.sidebar.toggle(
            "Mostrar paradas",
            value=True,
            key="mapa_mostrar_paradas",
        )

        if selected_vehicle != "Todos":
            day_df = day_df.loc[day_df["Veículo"].astype(str) == selected_vehicle].copy()

        if day_df.empty:
            st.warning("Nenhum dado encontrado para o veículo selecionado.")
            st.stop()

        enriched, stops = classify_stops(sort_records(day_df))
        routes = list(iter_vehicle_day_routes(enriched))

        if selected_vehicle == "Todos" and len(routes) > 1:
            _renderizar_todas_rotas(routes, stops, float(limite), mostrar_alertas, mostrar_paradas)
        else:
            vehicle, plate, route_date = routes[0][0]
            _renderizar_rota(
                routes[0][1],
                stops,
                vehicle,
                plate,
                route_date,
                float(limite),
                mostrar_alertas,
                mostrar_paradas,
            )
    except Exception as exc:
        st.error(f"Não foi possível renderizar o mapa: {exc}")


def _renderizar_rota(
    route_df: pd.DataFrame,
    stops: pd.DataFrame,
    vehicle: str,
    plate: str,
    route_date: object,
    limite: float,
    mostrar_alertas: bool,
    mostrar_paradas: bool,
) -> None:
    """Renderiza o mapa PyDeck e o painel de resumo para um único veículo."""
    route_stops = filter_stops_for_route(stops, vehicle, plate, route_date)
    summary = analyze_route(route_df, route_stops)
    stats = calculate_route_stats(route_df, route_stops, limite)

    layers, view_state = build_pydeck_layers(
        route_df,
        route_stops,
        limite,
        show_alerts=mostrar_alertas,
        show_stops=mostrar_paradas,
        veiculo_label=f"{vehicle} — {plate}",
    )

    deck = pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        map_style=_MAP_STYLE,
        tooltip=_TOOLTIP,
    )

    col_map, col_report = st.columns([3, 1])
    with col_map:
        st.pydeck_chart(deck, height=550)
    with col_report:
        _renderizar_cards_rota(summary, stats)


def _renderizar_todas_rotas(
    routes: list,
    stops: pd.DataFrame,
    limite: float,
    mostrar_alertas: bool,
    mostrar_paradas: bool,
) -> None:
    """Renderiza o mapa PyDeck com todos os veículos do dia e o painel de resumo."""
    layers, view_state = build_pydeck_layers_multi(
        routes,
        stops,
        limite,
        show_alerts=mostrar_alertas,
        show_stops=mostrar_paradas,
    )

    deck = pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        map_style=_MAP_STYLE,
        tooltip=_TOOLTIP,
    )

    total_registros = sum(len(route_df) for _, route_df in routes)
    total_alertas = sum(
        int((route_df["Velocidade"].astype(float) > limite).sum()) for _, route_df in routes
    )

    col_map, col_report = st.columns([3, 1])
    with col_map:
        st.pydeck_chart(deck, height=550)
    with col_report:
        st.subheader("Resumo do dia")
        st.metric("Veículos no mapa", len(routes))
        st.metric("Registros", f"{total_registros:,}".replace(",", "."))
        st.metric("Alertas", total_alertas)
        st.metric("Paradas", len(stops))


def _renderizar_cards_rota(summary: dict, stats: dict) -> None:
    """Exibe o resumo da rota em layout compacto e minimalista."""
    veiculo = summary.get("Veículo", "—")
    placa   = summary.get("Placa", "—")
    inicio  = summary.get("inicio")
    fim     = summary.get("fim")
    dist_km = float(summary.get("distancia_km", 0))
    t_mov   = float(summary.get("tempo_movimento_segundos", 0))
    t_par   = float(summary.get("tempo_parado_segundos", 0))

    vel_med = float(stats.get("velocidade_media", 0))
    vel_max = float(stats.get("velocidade_maxima", 0))
    alertas = int(stats.get("alertas_velocidade", 0))
    paradas = int(stats.get("quantidade_paradas", 0))
    dur_med = float(stats.get("duracao_media_parada_minutos", 0))
    ign_lig = float(stats.get("percentual_ignicao_ligada", 0))
    ign_des = float(stats.get("percentual_ignicao_desligada", 0))

    def _hm(seg: float) -> str:
        h, r = divmod(int(max(seg, 0)), 3600)
        return f"{h:02d}:{r // 60:02d}"

    hora_ini = inicio.strftime("%H:%M") if inicio else "—"
    hora_fim = fim.strftime("%H:%M")    if fim    else "—"
    dur_par  = f"{dur_med:.0f} min"     if paradas else "—"

    st.markdown(
        f"""
        <style>
        .resumo-rota {{font-family: sans-serif; font-size: 12px; color: #444; line-height: 1.8;}}
        .resumo-rota .titulo {{font-size: 15px; font-weight: 700; color: #111; margin-bottom: 2px;}}
        .resumo-rota .placa  {{font-size: 11px; color: #888; margin-bottom: 8px;}}
        .resumo-rota .secao  {{margin: 8px 0 4px; font-size: 10px; font-weight: 600;
                               text-transform: uppercase; letter-spacing: .5px; color: #aaa;}}
        .resumo-rota .linha  {{display: flex; justify-content: space-between; padding: 2px 0;
                               border-bottom: 1px solid #f0f0f0;}}
        .resumo-rota .label  {{color: #666;}}
        .resumo-rota .valor  {{font-weight: 600; color: #222;}}
        .alerta {{color: #e53e3e !important;}}
        </style>
        <div class="resumo-rota">
          <div class="titulo">🚛 {veiculo}</div>
          <div class="placa">Placa: {placa}</div>

          <div class="secao">Rota</div>
          <div class="linha"><span class="label">Distância</span><span class="valor">{dist_km:.1f} km</span></div>
          <div class="linha"><span class="label">Início</span><span class="valor">{hora_ini}</span></div>
          <div class="linha"><span class="label">Fim</span><span class="valor">{hora_fim}</span></div>

          <div class="secao">Velocidade</div>
          <div class="linha"><span class="label">Média</span><span class="valor">{vel_med:.1f} km/h</span></div>
          <div class="linha"><span class="label">Máxima</span><span class="valor">{vel_max:.1f} km/h</span></div>
          <div class="linha"><span class="label">Alertas</span>
            <span class="valor {'alerta' if alertas > 0 else ''}">{alertas}</span></div>

          <div class="secao">Tempo</div>
          <div class="linha"><span class="label">Movimento</span><span class="valor">{_hm(t_mov)}</span></div>
          <div class="linha"><span class="label">Parado</span><span class="valor">{_hm(t_par)}</span></div>

          <div class="secao">Paradas</div>
          <div class="linha"><span class="label">Quantidade</span><span class="valor">{paradas}</span></div>
          <div class="linha"><span class="label">Duração média</span><span class="valor">{dur_par}</span></div>

          <div class="secao">Ignição</div>
          <div class="linha"><span class="label">🟢 Ligada</span><span class="valor">{ign_lig:.1f}%</span></div>
          <div class="linha"><span class="label">🔴 Desligada</span><span class="valor">{ign_des:.1f}%</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


main()

# ALTERAÇÕES:
# - Folium e streamlit.components.v1 removidos: mapa agora usa st.pydeck_chart()
#   diretamente (WebGL via deck.gl, sem iframe nem serialização HTML).
# - build_route_map_html removida do import; substituída por build_pydeck_layers
#   e build_pydeck_layers_multi.
# - SPEED_BANDS removido do import (lógica de cores encapsulada em map_builder.py).
# - _renderizar_rota: usa build_pydeck_layers + pdk.Deck + st.pydeck_chart.
# - _renderizar_todas_rotas: usa build_pydeck_layers_multi + pdk.Deck + st.pydeck_chart.
# - _build_combined_map_html, _adicionar_polylines_agrupadas, _cor_por_velocidade
#   removidos: responsabilidade migrada para map_builder.py.
# - Dados carregados via consultar_dados(selected_day, selected_day): apenas o dia
#   selecionado, sem carregar o dataset completo.
# - _MAP_STYLE importado de map_builder para consistência com o CLI.


