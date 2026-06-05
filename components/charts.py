"""Gráficos Plotly reutilizáveis do portal — dark theme."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config import ROUTE_DATE_COLUMN

_BG = "#111318"
_PAPER = "#0a0c10"
_GRID = "#1e2229"
_TEXT = "#7a8099"
_TITLE_COLOR = "#e8eaf0"
_ACCENT = "#00e5a0"
_WARN = "#ff6b35"
_INFO = "#4da6ff"


def _dark_layout(fig: go.Figure, title: str = "") -> go.Figure:
    """Aplica o layout dark padrão a uma figura Plotly."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=_PAPER,
        plot_bgcolor=_BG,
        margin=dict(l=8, r=8, t=40, b=8),
        title=dict(
            text=title,
            font=dict(family="Syne, sans-serif", size=13, color=_TITLE_COLOR),
            x=0,
            xanchor="left",
        ),
        font=dict(family="Space Mono, monospace", size=10, color=_TEXT),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor=_GRID,
            borderwidth=1,
            font=dict(size=10, color=_TEXT),
        ),
        xaxis=dict(
            gridcolor=_GRID,
            linecolor=_GRID,
            tickfont=dict(size=9, color=_TEXT),
            zeroline=False,
        ),
        yaxis=dict(
            gridcolor=_GRID,
            linecolor=_GRID,
            tickfont=dict(size=9, color=_TEXT),
            zeroline=False,
        ),
    )
    return fig


def grafico_km_por_veiculo(resumo_diario: pd.DataFrame) -> go.Figure:
    """Gráfico de barras com km total por veículo."""
    if resumo_diario.empty:
        return _figura_vazia("Km por veículo")

    data = (
        resumo_diario.groupby("Veículo", as_index=False)["km_total"]
        .sum()
        .sort_values("km_total", ascending=False)
    )
    fig = go.Figure(
        go.Bar(
            x=data["Veículo"],
            y=data["km_total"],
            marker_color=_ACCENT,
            marker_line_width=0,
            text=data["km_total"].round(1),
            textfont=dict(size=10, color=_TEXT),
            textposition="outside",
        )
    )
    _dark_layout(fig, "Km por veículo")
    fig.update_layout(yaxis_title="km", xaxis_title="")
    return fig


def grafico_evolucao_diaria(resumo_diario: pd.DataFrame) -> go.Figure:
    """Gráfico de linha com km total da frota por dia."""
    if resumo_diario.empty:
        return _figura_vazia("Evolução diária")

    data = resumo_diario.groupby(ROUTE_DATE_COLUMN, as_index=False)["km_total"].sum()
    fig = go.Figure(
        go.Scatter(
            x=data[ROUTE_DATE_COLUMN],
            y=data["km_total"],
            mode="lines+markers",
            line=dict(color=_ACCENT, width=2),
            marker=dict(color=_ACCENT, size=6),
            fill="tozeroy",
            fillcolor="rgba(0,229,160,0.08)",
        )
    )
    _dark_layout(fig, "Evolução diária de km")
    fig.update_layout(yaxis_title="km", xaxis_title="")
    return fig


def grafico_ranking_alertas(resumo_diario: pd.DataFrame) -> go.Figure:
    """Ranking horizontal de alertas de velocidade."""
    if resumo_diario.empty:
        return _figura_vazia("Ranking de alertas")

    data = (
        resumo_diario.groupby("Veículo", as_index=False)["alertas_velocidade"]
        .sum()
        .sort_values("alertas_velocidade", ascending=True)
    )
    fig = go.Figure(
        go.Bar(
            x=data["alertas_velocidade"],
            y=data["Veículo"],
            orientation="h",
            marker_color=_WARN,
            marker_line_width=0,
        )
    )
    _dark_layout(fig, "Ranking de alertas de velocidade")
    fig.update_layout(xaxis_title="alertas", yaxis_title="")
    return fig


def grafico_ignicao(resumo_diario: pd.DataFrame) -> go.Figure:
    """Barras empilhadas de ignição ligada e desligada por veículo."""
    if resumo_diario.empty:
        return _figura_vazia("Ignição por veículo")

    data = resumo_diario.groupby("Veículo", as_index=False)[
        ["horas_ignicao_ligada", "horas_ignicao_desligada"]
    ].sum()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Ligada",
        x=data["Veículo"],
        y=data["horas_ignicao_ligada"],
        marker_color=_ACCENT,
        marker_line_width=0,
    ))
    fig.add_trace(go.Bar(
        name="Desligada",
        x=data["Veículo"],
        y=data["horas_ignicao_desligada"],
        marker_color=_WARN,
        marker_line_width=0,
    ))
    _dark_layout(fig, "Horas de ignição por veículo")
    fig.update_layout(barmode="stack", yaxis_title="horas", xaxis_title="")
    return fig


@st.cache_data(ttl=300)
def _preparar_dados_heatmap(df: pd.DataFrame) -> pd.DataFrame:
    """Prepara o pivot table para o heatmap de atividade (resultado cacheado)."""
    nomes = {
        "Monday": "Segunda", "Tuesday": "Terça", "Wednesday": "Quarta",
        "Thursday": "Quinta", "Friday": "Sexta", "Saturday": "Sábado", "Sunday": "Domingo",
    }
    ordem = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
    data = df[["Data da Coordenada"]].copy()
    data["hora"] = data["Data da Coordenada"].dt.hour
    data["dia_semana"] = data["Data da Coordenada"].dt.day_name().map(nomes)
    return (
        data.groupby(["dia_semana", "hora"])
        .size()
        .reset_index(name="coordenadas")
        .pivot(index="dia_semana", columns="hora", values="coordenadas")
        .reindex(ordem)
        .fillna(0)
    )


def heatmap_atividade(df: pd.DataFrame) -> go.Figure:
    """Heatmap de atividade por hora e dia da semana."""
    if df.empty:
        return _figura_vazia("Heatmap de atividade")

    pivot = _preparar_dados_heatmap(df)
    fig = px.imshow(
        pivot,
        aspect="auto",
        color_continuous_scale=[[0, _BG], [0.3, "#003d29"], [1, _ACCENT]],
        title="Atividade da frota por dia e hora",
    )
    _dark_layout(fig, "Atividade da frota por dia e hora")
    fig.update_layout(
        xaxis_title="hora do dia",
        yaxis_title="",
        coloraxis_showscale=False,
    )
    return fig


def grafico_comparativo(
    resumo_a: pd.DataFrame,
    resumo_b: pd.DataFrame,
    label_a: str,
    label_b: str,
) -> go.Figure:
    """Compara km total e alertas por veículo entre dois períodos."""
    if resumo_a.empty and resumo_b.empty:
        return _figura_vazia("Comparativo de períodos")

    data_a = _preparar_comparativo(resumo_a, label_a)
    data_b = _preparar_comparativo(resumo_b, label_b)
    data = pd.concat([data_a, data_b], ignore_index=True)

    fig = px.bar(
        data,
        x="Veículo",
        y="valor",
        color="período",
        facet_col="métrica",
        barmode="group",
        color_discrete_sequence=[_ACCENT, _INFO],
    )
    _dark_layout(fig, "Comparativo por veículo")
    fig.update_yaxes(matches=None, showticklabels=True)
    fig.update_layout(xaxis_title="", yaxis_title="")
    return fig


def grafico_velocidade_veiculo(df: pd.DataFrame) -> go.Figure:
    """Série temporal de velocidade para o veículo selecionado."""
    if df.empty:
        return _figura_vazia("Velocidade ao longo do tempo")

    data = df.sort_values("Data da Coordenada").copy()
    data["Velocidade"] = data["Velocidade"].astype(float)

    days = sorted(data[ROUTE_DATE_COLUMN].unique()) if ROUTE_DATE_COLUMN in data.columns else [None]
    colors_line = [_ACCENT, _INFO, _WARN, "#9b59b6", "#e67e22"]
    colors_fill = [
        "rgba(0,229,160,0.08)", "rgba(77,166,255,0.08)",
        "rgba(255,107,53,0.08)", "rgba(155,89,182,0.08)", "rgba(230,126,34,0.08)",
    ]

    fig = go.Figure()
    for i, day in enumerate(days):
        day_data = data[data[ROUTE_DATE_COLUMN] == day] if day is not None else data
        color_l = colors_line[i % len(colors_line)]
        color_f = colors_fill[i % len(colors_fill)]
        name = pd.to_datetime(day).strftime("%d/%m") if day is not None else "rota"
        fig.add_trace(go.Scatter(
            x=day_data["Data da Coordenada"],
            y=day_data["Velocidade"],
            mode="lines",
            name=name,
            line=dict(color=color_l, width=1.5),
            fill="tozeroy",
            fillcolor=color_f,
        ))

    _dark_layout(fig, "Velocidade ao longo do tempo")
    fig.update_layout(
        yaxis_title="km/h",
        xaxis_title="",
        showlegend=len(days) > 1,
    )
    return fig


def grafico_velocidade_diaria(resumo: pd.DataFrame) -> go.Figure:
    """Linha de velocidade máxima por dia."""
    if resumo.empty:
        return _figura_vazia("Velocidade máxima por dia")

    fig = go.Figure(go.Scatter(
        x=resumo[ROUTE_DATE_COLUMN],
        y=resumo["velocidade_maxima"],
        mode="lines+markers",
        line=dict(color=_WARN, width=2),
        marker=dict(color=_WARN, size=6),
    ))
    _dark_layout(fig, "Velocidade máxima por dia")
    fig.update_layout(yaxis_title="km/h", xaxis_title="")
    return fig


def grafico_paradas_diarias(resumo: pd.DataFrame) -> go.Figure:
    """Barras de quantidade de paradas por dia."""
    if resumo.empty:
        return _figura_vazia("Paradas por dia")

    fig = go.Figure(go.Bar(
        x=resumo[ROUTE_DATE_COLUMN],
        y=resumo["quantidade_paradas"],
        marker_color=_INFO,
        marker_line_width=0,
    ))
    _dark_layout(fig, "Paradas por dia")
    fig.update_layout(yaxis_title="paradas", xaxis_title="")
    return fig


def _preparar_comparativo(resumo: pd.DataFrame, label: str) -> pd.DataFrame:
    if resumo.empty:
        return pd.DataFrame(columns=["Veículo", "métrica", "valor", "período"])

    grouped = resumo.groupby("Veículo", as_index=False).agg(
        km_total=("km_total", "sum"),
        alertas_velocidade=("alertas_velocidade", "sum"),
    )
    long = grouped.melt(
        id_vars="Veículo",
        value_vars=["km_total", "alertas_velocidade"],
        var_name="métrica",
        value_name="valor",
    )
    long["métrica"] = long["métrica"].replace(
        {"km_total": "Km total", "alertas_velocidade": "Alertas"}
    )
    long["período"] = label
    return long


def _figura_vazia(titulo: str) -> go.Figure:
    fig = go.Figure()
    _dark_layout(fig, titulo)
    fig.add_annotation(
        text="Sem dados para exibir",
        xref="paper", yref="paper",
        x=0.5, y=0.5,
        showarrow=False,
        font=dict(color=_TEXT, size=12),
    )
    return fig
