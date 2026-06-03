"""Geração de mapas: Folium para o CLI, PyDeck para o portal Streamlit."""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any

import pandas as pd

from config import IS_STOP_COLUMN, LATITUDE_COLUMN, LONGITUDE_COLUMN, SPEED_BANDS, STOP_ID_COLUMN
from utils.helpers import ensure_directory

try:
    import folium
except ModuleNotFoundError:  # pragma: no cover
    folium = None  # type: ignore[assignment]

try:
    import pydeck as pdk
except ModuleNotFoundError:  # pragma: no cover
    pdk = None  # type: ignore[assignment]

# Paleta de cores para identificar veículos distintos no mapa multi-veículo
PALETA_VEICULOS: list[list[int]] = [
    [31, 119, 180],   # azul
    [255, 127, 14],   # laranja
    [44, 160, 44],    # verde
    [214, 39, 40],    # vermelho
    [148, 103, 189],  # roxo
    [140, 86, 75],    # marrom
    [227, 119, 194],  # rosa
    [127, 127, 127],  # cinza
    [188, 189, 34],   # oliva
    [23, 190, 207],   # ciano
]

# Mapa de estilo sem necessidade de token Mapbox
_MAP_STYLE = "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"


# ---------------------------------------------------------------------------
# API pública — Folium (CLI)
# ---------------------------------------------------------------------------

def build_route_map(
    route_df: pd.DataFrame,
    stops_df: pd.DataFrame,
    output_path: str | Path,
    speed_limit: float,
) -> Path:
    """Gera um mapa HTML interativo para uma rota e salva em disco.

    Mantido para uso pelo CLI (main_cli.py). Usa Folium.

    Args:
        route_df: DataFrame da rota.
        stops_df: DataFrame de paradas da rota.
        output_path: Caminho do arquivo HTML de saída.
        speed_limit: Limite para destacar alertas de velocidade.

    Returns:
        Caminho do mapa salvo.

    Raises:
        ValueError: Quando a rota não possui registros.
        RuntimeError: Quando a dependência Folium não está instalada.
    """
    if folium is None:
        raise RuntimeError(
            "A biblioteca folium não está instalada. Execute: pip install -r requirements.txt"
        )
    if route_df.empty:
        raise ValueError("Não há registros para gerar o mapa.")

    route = route_df.sort_values("Data da Coordenada").reset_index(drop=True).copy()
    center = [float(route[LATITUDE_COLUMN].median()), float(route[LONGITUDE_COLUMN].median())]

    route_map = folium.Map(location=center, zoom_start=13, control_scale=True)
    _add_speed_polylines(route_map, route)
    _add_start_end_markers(route_map, route)
    _add_stop_circles(route_map, stops_df)
    _add_speed_alerts(route_map, route, speed_limit)

    bounds = route[[LATITUDE_COLUMN, LONGITUDE_COLUMN]].dropna().values.tolist()
    if bounds:
        route_map.fit_bounds(bounds, padding=(30, 30))

    output = Path(output_path)
    ensure_directory(output.parent)
    route_map.save(str(output))
    return output


# ---------------------------------------------------------------------------
# API pública — PyDeck (portal Streamlit)
# ---------------------------------------------------------------------------

def build_pydeck_layers(
    route_df: pd.DataFrame,
    stops_df: pd.DataFrame,
    speed_limit: float,
    show_alerts: bool = True,
    show_stops: bool = True,
    veiculo_label: str = "",
    min_ignicao_off_min: float = 0.0,
    min_ignicao_on_min: float = 0.0,
) -> tuple[list, Any]:
    """Constrói as camadas PyDeck para uma única rota.

    Args:
        route_df: DataFrame da rota ordenado por Data da Coordenada.
        stops_df: DataFrame de paradas da rota (já filtrado por veículo/dia).
        speed_limit: Limite para alertas de velocidade.
        show_alerts: Se True, inclui camada de alertas.
        show_stops: Se True, inclui camada de paradas.
        veiculo_label: Nome do veículo para tooltips.
        min_ignicao_off_min: Duração mínima (min) para exibir parada com ignição desligada.

    Returns:
        Tupla (lista de layers pydeck, pdk.ViewState centralizado na rota).

    Raises:
        RuntimeError: Quando pydeck não está instalado.
    """
    _verificar_pydeck()

    route = route_df.sort_values("Data da Coordenada").reset_index(drop=True).copy()
    layers: list = []

    # Rota colorida por faixa de velocidade (PathLayer por segmento contíguo)
    segmentos = _segmentar_por_velocidade(route)
    if segmentos:
        layers.append(
            pdk.Layer(
                "PathLayer",
                data=segmentos,
                get_path="path",
                get_color="color",
                get_width=5,
                width_min_pixels=3,
                pickable=False,
                auto_highlight=False,
            )
        )

    # Pontos invisíveis e pickables para exibir velocidade ao passar o mouse
    layers.append(_camada_pontos_velocidade(route))

    # Marcadores de início e fim
    if not route.empty:
        layers.append(_camada_marcadores(route, prefix=veiculo_label))

    # Alertas de velocidade
    if show_alerts:
        layer_alertas = _camada_alertas(route, speed_limit)
        if layer_alertas is not None:
            layers.append(layer_alertas)

    # Paradas
    if show_stops and not stops_df.empty:
        layers.append(_camada_paradas(stops_df))

    # Paradas com ignição desligada — círculos laranjas
    layer_ignicao_off = _camada_ignicao_desligada(route, min_ignicao_off_min)
    if layer_ignicao_off is not None:
        layers.append(layer_ignicao_off)

    # Paradas com ignição ligada (motor ocioso) — círculos amarelos
    layer_ignicao_on = _camada_ignicao_ligada(route, min_ignicao_on_min)
    if layer_ignicao_on is not None:
        layers.append(layer_ignicao_on)

    view_state = pdk.ViewState(
        latitude=float(route[LATITUDE_COLUMN].median()),
        longitude=float(route[LONGITUDE_COLUMN].median()),
        zoom=13,
        pitch=0,
    )

    return layers, view_state


def build_pydeck_layers_multi(
    routes: list[tuple[tuple, pd.DataFrame]],
    stops_df: pd.DataFrame,
    speed_limit: float,
    show_alerts: bool = True,
    show_stops: bool = True,
    min_ignicao_off_min: float = 0.0,
    min_ignicao_on_min: float = 0.0,
) -> tuple[list, Any]:
    """Constrói camadas PyDeck para múltiplos veículos.

    Cada veículo recebe uma cor distinta da paleta PALETA_VEICULOS.
    A rota de cada veículo é uma PathLayer na cor do veículo (sem segmentação
    por velocidade, pois cores distintas já identificam cada veículo).

    Args:
        routes: Lista de (chave, DataFrame) retornada por iter_vehicle_day_routes.
        stops_df: DataFrame de todas as paradas do dia.
        speed_limit: Limite para alertas.
        show_alerts: Se True, inclui camada de alertas por veículo.
        show_stops: Se True, inclui camada de paradas geral.
        min_ignicao_off_min: Duração mínima (min) para exibir parada com ignição desligada.

    Returns:
        Tupla (lista de layers, pdk.ViewState centrado em todos os pontos).

    Raises:
        RuntimeError: Quando pydeck não está instalado.
    """
    _verificar_pydeck()

    layers: list = []
    all_lats: list[float] = []
    all_lons: list[float] = []

    for idx, ((vehicle, plate, _), route_df) in enumerate(routes):
        cor = PALETA_VEICULOS[idx % len(PALETA_VEICULOS)]
        route = route_df.sort_values("Data da Coordenada").reset_index(drop=True).copy()

        lats = route[LATITUDE_COLUMN].dropna().tolist()
        lons = route[LONGITUDE_COLUMN].dropna().tolist()
        all_lats.extend(lats)
        all_lons.extend(lons)

        if len(lons) >= 2:
            path_data = [
                {
                    "path": [
                        [float(lon), float(lat)]
                        for lat, lon in zip(lats, lons)
                    ],
                    "veiculo": str(vehicle),
                    "color": cor,
                }
            ]
            layers.append(
                pdk.Layer(
                    "PathLayer",
                    data=path_data,
                    get_path="path",
                    get_color="color",
                    get_width=4,
                    width_min_pixels=2,
                    pickable=True,
                    auto_highlight=True,
                )
            )

        # Pontos invisíveis e pickables para exibir velocidade ao passar o mouse
        layers.append(_camada_pontos_velocidade(route))

        # Marcadores de início e fim do veículo
        if not route.empty:
            layers.append(_camada_marcadores(route, prefix=str(vehicle)))

        # Alertas individuais por veículo
        if show_alerts:
            layer_alertas = _camada_alertas(route, speed_limit, veiculo=str(vehicle))
            if layer_alertas is not None:
                layers.append(layer_alertas)

        # Paradas com ignição desligada — laranjas
        layer_ignicao_off = _camada_ignicao_desligada(route, min_ignicao_off_min)
        if layer_ignicao_off is not None:
            layers.append(layer_ignicao_off)

        # Paradas com ignição ligada (motor ocioso) — amarelas
        layer_ignicao_on = _camada_ignicao_ligada(route, min_ignicao_on_min)
        if layer_ignicao_on is not None:
            layers.append(layer_ignicao_on)

    # Paradas de todos os veículos do dia
    if show_stops and not stops_df.empty:
        layers.append(_camada_paradas(stops_df))

    # ViewState centralizado no conjunto de todos os pontos
    if all_lats:
        center_lat = float(pd.Series(all_lats).median())
        center_lon = float(pd.Series(all_lons).median())
    else:
        center_lat, center_lon = -15.0, -50.0

    view_state = pdk.ViewState(
        latitude=center_lat,
        longitude=center_lon,
        zoom=12,
        pitch=0,
    )

    return layers, view_state


# ---------------------------------------------------------------------------
# Helpers internos — PyDeck
# ---------------------------------------------------------------------------

def _verificar_pydeck() -> None:
    if pdk is None:
        raise RuntimeError(
            "A biblioteca pydeck não está instalada. Execute: pip install -r requirements.txt"
        )


def _segmentar_por_velocidade(route: pd.DataFrame) -> list[dict]:
    """Agrupa pontos consecutivos da rota em segmentos contíguos por faixa de velocidade.

    Retorna lista de dicts {"path": [[lon, lat], ...], "color": [r, g, b]}
    prontos para PathLayer do PyDeck.

    ATENÇÃO: PyDeck usa [longitude, latitude] — ordem inversa ao Folium.
    """
    if len(route) < 2:
        return []

    # Extrai arrays: longitude, latitude, velocidade
    lons = route[LONGITUDE_COLUMN].astype(float).values
    lats = route[LATITUDE_COLUMN].astype(float).values
    vels = route["Velocidade"].astype(float).values

    segmentos: list[dict] = []
    current_color = _cor_velocidade_rgb(vels[0])
    current_path: list[list[float]] = [[lons[0], lats[0]]]

    for i in range(1, len(vels)):
        pt_color = _cor_velocidade_rgb(vels[i])

        if pt_color == current_color:
            # Mesmo segmento — apenas estende o caminho
            current_path.append([lons[i], lats[i]])
        else:
            # Transição de faixa — fecha o segmento atual com ponto de conexão
            current_path.append([lons[i], lats[i]])
            segmentos.append({"path": current_path, "color": current_color})
            # Novo segmento começa no ponto anterior (continuidade visual)
            current_path = [[lons[i - 1], lats[i - 1]], [lons[i], lats[i]]]
            current_color = pt_color

    if len(current_path) >= 2:
        segmentos.append({"path": current_path, "color": current_color})

    return segmentos


def _camada_marcadores(route: pd.DataFrame, prefix: str = "") -> Any:
    """Cria ScatterplotLayer com marcadores de início (verde) e fim (vermelho)."""
    inicio = route.iloc[0]
    fim = route.iloc[-1]
    label_inicio = f"▶ Início {prefix}".strip()
    label_fim = f"■ Fim {prefix}".strip()

    markers = [
        {
            "lon": float(inicio[LONGITUDE_COLUMN]),
            "lat": float(inicio[LATITUDE_COLUMN]),
            "label": label_inicio,
            "color": [39, 174, 96],
        },
        {
            "lon": float(fim[LONGITUDE_COLUMN]),
            "lat": float(fim[LATITUDE_COLUMN]),
            "label": label_fim,
            "color": [192, 57, 43],
        },
    ]
    return pdk.Layer(
        "ScatterplotLayer",
        data=markers,
        get_position=["lon", "lat"],
        get_fill_color="color",
        get_radius=60,
        pickable=True,
        auto_highlight=True,
    )


def _camada_alertas(
    route: pd.DataFrame,
    speed_limit: float,
    veiculo: str = "",
) -> Any | None:
    """Cria ScatterplotLayer laranja com pontos acima do limite de velocidade.

    Retorna None quando não há alertas.
    """
    alertas = route.loc[route["Velocidade"].astype(float) > speed_limit].copy()
    if alertas.empty:
        return None

    vel = alertas["Velocidade"].astype(float).round(1)
    prefixo = f"{veiculo} — " if veiculo else ""
    data = pd.DataFrame({
        "lon": alertas[LONGITUDE_COLUMN].astype(float).values,
        "lat": alertas[LATITUDE_COLUMN].astype(float).values,
        "label": (prefixo + "⚠️ " + vel.astype(str) + " km/h").values,
    })

    return pdk.Layer(
        "ScatterplotLayer",
        data=data,
        get_position=["lon", "lat"],
        get_fill_color=[237, 137, 54, 200],
        get_line_color=[200, 100, 30],
        get_radius=30,
        pickable=True,
        stroked=True,
        filled=True,
    )


def _camada_ignicao_desligada(
    route: pd.DataFrame,
    min_minutos: float = 0.0,
) -> Any | None:
    """ScatterplotLayer laranja para paradas onde a ignição estava desligada.

    Usa o DataFrame enriquecido pelo classify_stops (que contém as colunas
    IS_STOP_COLUMN e STOP_ID_COLUMN). Cada parada com ignição off é
    representada por um círculo laranja no ponto mediano da sequência.

    Args:
        route: DataFrame enriquecido com colunas de parada.
        min_minutos: Duração mínima em minutos para exibir a parada.

    Retorna None quando o DataFrame não vem de classify_stops,
    não há paradas com ignição desligada ou nenhuma atinge o tempo mínimo.
    """
    # Só funciona com o DataFrame enriquecido (tem as colunas de parada)
    if IS_STOP_COLUMN not in route.columns or STOP_ID_COLUMN not in route.columns:
        return None

    ignicao_off = route["Ignição"].astype(str).str.strip().str.casefold() == "desligada"
    parada_off = route.loc[route[IS_STOP_COLUMN] & ignicao_off]

    if parada_off.empty:
        return None

    # Um ponto representativo por parada (mediana de lat/lon + duração real)
    def _duracao_min(x: pd.Series) -> float:
        delta = x.max() - x.min()
        return round(delta.total_seconds() / 60, 1)

    grouped = (
        parada_off.groupby(STOP_ID_COLUMN, observed=True)
        .agg(
            lon=(LONGITUDE_COLUMN, "median"),
            lat=(LATITUDE_COLUMN, "median"),
            duracao_min=("Data da Coordenada", _duracao_min),
        )
        .reset_index()
    )
    # Aplica filtro de duração mínima
    if min_minutos > 0:
        grouped = grouped.loc[grouped["duracao_min"] >= min_minutos]

    if grouped.empty:
        return None

    grouped["radius"] = 60  # raio fixo em metros
    grouped["label"] = (
        "🔴 Ignição desligada — " + grouped["duracao_min"].astype(str) + " min"
    )
    # Campo vazio para evitar que o tooltip global mostre {Velocidade} literal
    grouped["Velocidade"] = ""

    return pdk.Layer(
        "ScatterplotLayer",
        data=grouped,
        get_position=["lon", "lat"],
        get_radius="radius",
        get_fill_color=[237, 137, 54, 190],   # laranja semitransparente
        get_line_color=[200, 90, 20],
        line_width_min_pixels=1,
        pickable=True,
        stroked=True,
        filled=True,
        auto_highlight=True,
    )


def _camada_pontos_velocidade(route: pd.DataFrame) -> Any:
    """ScatterplotLayer invisível e pickable sobre cada ponto da rota.

    Raio de 25 m por ponto — transparente visualmente mas detectável
    pelo hover do PyDeck. O tooltip exibe a velocidade exata naquele
    ponto GPS ao passar o mouse sobre a linha de deslocamento.
    """
    data = pd.DataFrame({
        "lon": route[LONGITUDE_COLUMN].astype(float).values,
        "lat": route[LATITUDE_COLUMN].astype(float).values,
        "label": (
            "🚗 " + route["Velocidade"].astype(float).round(1).astype(str) + " km/h"
        ).values,
        "Velocidade": "",  # campo vazio — velocidade já está no label
    })
    return pdk.Layer(
        "ScatterplotLayer",
        data=data,
        get_position=["lon", "lat"],
        get_radius=25,
        get_fill_color=[0, 0, 0, 0],   # completamente transparente
        pickable=True,
        stroked=False,
        filled=True,
        auto_highlight=False,
    )


def _camada_ignicao_ligada(
    route: pd.DataFrame,
    min_minutos: float = 0.0,
) -> Any | None:
    """ScatterplotLayer amarela para paradas onde a ignição estava ligada (motor ocioso).

    Args:
        route: DataFrame enriquecido com colunas de parada.
        min_minutos: Duração mínima em minutos para exibir a parada.

    Retorna None quando não há paradas com ignição ligada ou nenhuma
    atinge o tempo mínimo.
    """
    if IS_STOP_COLUMN not in route.columns or STOP_ID_COLUMN not in route.columns:
        return None

    ignicao_on = route["Ignição"].astype(str).str.strip().str.casefold() == "ligada"
    parada_on = route.loc[route[IS_STOP_COLUMN] & ignicao_on]

    if parada_on.empty:
        return None

    def _duracao_min(x: pd.Series) -> float:
        delta = x.max() - x.min()
        return round(delta.total_seconds() / 60, 1)

    grouped = (
        parada_on.groupby(STOP_ID_COLUMN, observed=True)
        .agg(
            lon=(LONGITUDE_COLUMN, "median"),
            lat=(LATITUDE_COLUMN, "median"),
            duracao_min=("Data da Coordenada", _duracao_min),
        )
        .reset_index()
    )

    if min_minutos > 0:
        grouped = grouped.loc[grouped["duracao_min"] >= min_minutos]

    if grouped.empty:
        return None

    grouped["radius"] = 60  # raio fixo em metros
    grouped["label"] = (
        "🟡 Ignição ligada parada — " + grouped["duracao_min"].astype(str) + " min"
    )
    grouped["Velocidade"] = ""

    return pdk.Layer(
        "ScatterplotLayer",
        data=grouped,
        get_position=["lon", "lat"],
        get_radius="radius",
        get_fill_color=[246, 173, 85, 190],   # amarelo âmbar semitransparente
        get_line_color=[200, 130, 20],
        line_width_min_pixels=1,
        pickable=True,
        stroked=True,
        filled=True,
        auto_highlight=True,
    )


def _camada_paradas(stops_df: pd.DataFrame) -> Any:
    """Cria ScatterplotLayer azul com círculos proporcionais à duração da parada."""
    data = pd.DataFrame({
        "lon": stops_df[LONGITUDE_COLUMN].astype(float).values,
        "lat": stops_df[LATITUDE_COLUMN].astype(float).values,
        "duracao_minutos": stops_df["duracao_minutos"].astype(float).values,
        "radius": 60,  # raio fixo em metros
        "label": ("Parada: " + stops_df["duracao_minutos"].astype(float).round(1).astype(str) + " min").values,
    })

    return pdk.Layer(
        "ScatterplotLayer",
        data=data,
        get_position=["lon", "lat"],
        get_radius="radius",
        get_fill_color=[43, 108, 176, 160],
        get_line_color=[43, 108, 176],
        pickable=True,
        stroked=True,
        filled=True,
        auto_highlight=True,
    )


def _cor_velocidade_rgb(speed: float) -> list[int]:
    """Retorna cor [r, g, b] para a faixa de velocidade do ponto."""
    for minimum, maximum, _, hex_color in SPEED_BANDS:
        if minimum <= speed <= maximum:
            return _hex_para_rgb(hex_color)
    return _hex_para_rgb(SPEED_BANDS[-1][3])


def _hex_para_rgb(hex_color: str) -> list[int]:
    """Converte cor hexadecimal (#rrggbb) para lista [r, g, b]."""
    h = hex_color.lstrip("#")
    return [int(h[i : i + 2], 16) for i in (0, 2, 4)]


# ---------------------------------------------------------------------------
# Helpers internos — Folium (usados somente por build_route_map)
# ---------------------------------------------------------------------------

def _add_speed_polylines(route_map: Any, route: pd.DataFrame) -> None:
    for index in range(1, len(route)):
        previous = route.iloc[index - 1]
        current = route.iloc[index]
        points = [
            [float(previous[LATITUDE_COLUMN]), float(previous[LONGITUDE_COLUMN])],
            [float(current[LATITUDE_COLUMN]), float(current[LONGITUDE_COLUMN])],
        ]
        speed = float(current["Velocidade"])
        folium.PolyLine(
            points,
            color=_speed_color(speed),
            weight=5,
            opacity=0.85,
            tooltip=f"{speed:.1f} km/h",
        ).add_to(route_map)


def _add_start_end_markers(route_map: Any, route: pd.DataFrame) -> None:
    start = route.iloc[0]
    end = route.iloc[-1]

    folium.Marker(
        location=[float(start[LATITUDE_COLUMN]), float(start[LONGITUDE_COLUMN])],
        popup=_point_popup(start, "Início da rota"),
        tooltip="Início",
        icon=folium.Icon(color="green", icon="play"),
    ).add_to(route_map)

    folium.Marker(
        location=[float(end[LATITUDE_COLUMN]), float(end[LONGITUDE_COLUMN])],
        popup=_point_popup(end, "Fim da rota"),
        tooltip="Fim",
        icon=folium.Icon(color="red", icon="stop"),
    ).add_to(route_map)


def _add_stop_circles(route_map: Any, stops_df: pd.DataFrame) -> None:
    if stops_df.empty:
        return

    for _, stop in stops_df.iterrows():
        duration = float(stop["duracao_minutos"])
        radius = max(6.0, min(28.0, 6.0 + duration / 5.0))
        popup = folium.Popup(
            "<strong>Parada</strong><br>"
            f"Início: {stop['inicio']:%d/%m/%Y %H:%M:%S}<br>"
            f"Fim: {stop['fim']:%d/%m/%Y %H:%M:%S}<br>"
            f"Duração: {duration:.1f} min",
            max_width=280,
        )
        folium.CircleMarker(
            location=[float(stop[LATITUDE_COLUMN]), float(stop[LONGITUDE_COLUMN])],
            radius=radius,
            color="#2b6cb0",
            fill=True,
            fill_color="#2b6cb0",
            fill_opacity=0.35,
            popup=popup,
            tooltip=f"Parada: {duration:.1f} min",
        ).add_to(route_map)


def _add_speed_alerts(route_map: Any, route: pd.DataFrame, speed_limit: float) -> None:
    alerts = route.loc[route["Velocidade"].astype(float) > speed_limit]
    for _, point in alerts.iterrows():
        folium.Marker(
            location=[float(point[LATITUDE_COLUMN]), float(point[LONGITUDE_COLUMN])],
            popup=_point_popup(point, f"Alerta acima de {speed_limit:.0f} km/h"),
            tooltip=f"Alerta: {float(point['Velocidade']):.1f} km/h",
            icon=folium.Icon(color="orange", icon="exclamation-sign"),
        ).add_to(route_map)


def _speed_color(speed: float) -> str:
    for minimum, maximum, _, hex_color in SPEED_BANDS:
        if minimum <= speed <= maximum:
            return hex_color
    return SPEED_BANDS[-1][3]


def _point_popup(row: pd.Series, title: str) -> Any:
    address = _get_optional_address(row)
    address_line = f"<br>Endereço: {html.escape(address)}" if address else ""
    content = (
        f"<strong>{html.escape(title)}</strong><br>"
        f"Horário: {row['Data da Coordenada']:%d/%m/%Y %H:%M:%S}<br>"
        f"Velocidade: {float(row['Velocidade']):.1f} km/h"
        f"{address_line}"
    )
    return folium.Popup(content, max_width=300)


def _get_optional_address(row: pd.Series) -> str:
    for column in ("Endereço", "Endereco", "address"):
        value: Any = row.get(column)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""

# ALTERAÇÕES:
# - build_route_map_html() removida: substituída por build_pydeck_layers() e
#   build_pydeck_layers_multi() que usam PyDeck/WebGL em vez de Folium/iframe.
# - build_route_map() mantida intacta: continua usando Folium para o CLI.
# - Adicionadas funções PyDeck: build_pydeck_layers, build_pydeck_layers_multi,
#   _segmentar_por_velocidade, _camada_marcadores, _camada_alertas,
#   _camada_paradas, _cor_velocidade_rgb, _hex_para_rgb.
# - _segmentar_por_velocidade: agrupa pontos consecutivos em segmentos por faixa
#   de velocidade, produzindo no máximo 3N segmentos para uma PathLayer eficiente.
# - PALETA_VEICULOS: 10 cores distintas para identificar veículos no modo multi.
# - Ordem de coordenadas: [longitude, latitude] em todos os layers PyDeck
#   (inverso ao Folium que usa [latitude, longitude]).
# - map_style: CARTO Positron (sem necessidade de token Mapbox).
