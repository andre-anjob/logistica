"""Gráficos Plotly reutilizáveis do portal."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config import ROUTE_DATE_COLUMN


def grafico_km_por_veiculo(resumo_diario: pd.DataFrame) -> go.Figure:
    """Cria gráfico de barras com km total por veículo."""
    if resumo_diario.empty:
        return _figura_vazia("Km por veículo")

    data = (
        resumo_diario.groupby("Veículo", as_index=False)["km_total"]
        .sum()
        .sort_values("km_total", ascending=False)
    )
    fig = px.bar(data, x="Veículo", y="km_total", text_auto=".1f", title="Km por veículo")
    fig.update_layout(yaxis_title="Km", xaxis_title="Veículo")
    return fig


def grafico_evolucao_diaria(resumo_diario: pd.DataFrame) -> go.Figure:
    """Cria gráfico de linha com km total da frota por dia."""
    if resumo_diario.empty:
        return _figura_vazia("Evolução diária")

    data = resumo_diario.groupby(ROUTE_DATE_COLUMN, as_index=False)["km_total"].sum()
    fig = px.line(
        data,
        x=ROUTE_DATE_COLUMN,
        y="km_total",
        markers=True,
        title="Evolução diária de km",
    )
    fig.update_layout(yaxis_title="Km", xaxis_title="Data")
    return fig


def grafico_ranking_alertas(resumo_diario: pd.DataFrame) -> go.Figure:
    """Cria ranking horizontal de alertas de velocidade."""
    if resumo_diario.empty:
        return _figura_vazia("Ranking de alertas")

    data = (
        resumo_diario.groupby("Veículo", as_index=False)["alertas_velocidade"]
        .sum()
        .sort_values("alertas_velocidade", ascending=True)
    )
    fig = px.bar(
        data,
        x="alertas_velocidade",
        y="Veículo",
        orientation="h",
        title="Ranking de alertas de velocidade",
    )
    fig.update_layout(xaxis_title="Alertas", yaxis_title="Veículo")
    return fig


def grafico_ignicao(resumo_diario: pd.DataFrame) -> go.Figure:
    """Cria barras empilhadas de ignição ligada e desligada por veículo."""
    if resumo_diario.empty:
        return _figura_vazia("Ignição por veículo")

    data = resumo_diario.groupby("Veículo", as_index=False)[
        ["horas_ignicao_ligada", "horas_ignicao_desligada"]
    ].sum()
    long = data.melt(
        id_vars="Veículo",
        value_vars=["horas_ignicao_ligada", "horas_ignicao_desligada"],
        var_name="estado",
        value_name="horas",
    )
    long["estado"] = long["estado"].replace(
        {
            "horas_ignicao_ligada": "Ligada",
            "horas_ignicao_desligada": "Desligada",
        }
    )
    fig = px.bar(
        long,
        x="Veículo",
        y="horas",
        color="estado",
        title="Horas de ignição por veículo",
    )
    fig.update_layout(yaxis_title="Horas", xaxis_title="Veículo", barmode="stack")
    return fig


def heatmap_atividade(df: pd.DataFrame) -> go.Figure:
    """Cria heatmap de atividade por hora e dia da semana."""
    if df.empty:
        return _figura_vazia("Heatmap de atividade")

    pivot = _preparar_dados_heatmap(df)
    fig = px.imshow(
        pivot,
        aspect="auto",
        color_continuous_scale="Blues",
        title="Atividade da frota por dia e hora",
    )
    fig.update_layout(xaxis_title="Hora do dia", yaxis_title="Dia da semana")
    return fig


@st.cache_data(ttl=300)
def _preparar_dados_heatmap(df: pd.DataFrame) -> pd.DataFrame:
    """Prepara o pivot table para o heatmap de atividade (resultado cacheado)."""
    nomes = {
        "Monday": "Segunda",
        "Tuesday": "Terça",
        "Wednesday": "Quarta",
        "Thursday": "Quinta",
        "Friday": "Sexta",
        "Saturday": "Sábado",
        "Sunday": "Domingo",
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
        title="Comparativo por veículo",
    )
    fig.update_yaxes(matches=None, showticklabels=True)
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
    fig.update_layout(title=titulo)
    fig.add_annotation(
        text="Sem dados para exibir",
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
    )
    return fig
