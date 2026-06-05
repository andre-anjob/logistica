"""Análise individual por veículo — dark theme."""

from __future__ import annotations

from datetime import timedelta
from io import BytesIO

import pandas as pd
import streamlit as st
from utils.styles import aplicar_estilos

from components.charts import (
    grafico_paradas_diarias,
    grafico_velocidade_diaria,
    grafico_velocidade_veiculo,
)
from components.kpi_cards import kpi_card_html
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
    aplicar_estilos()

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
            "Veículo", options=vehicles, key="analise_veiculo"
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
            min_value=40, max_value=140, value=80, step=5,
            key="analise_limite_velocidade",
        )

        filtrado = consultar_dados(data_inicio, data_fim, veiculos=[selected_vehicle])

        if filtrado.empty:
            st.warning("Nenhum dado encontrado para o veículo e período selecionados.")
            st.stop()

        kpis = calcular_kpis_veiculo(filtrado, selected_vehicle, float(limite))
        resumo = calcular_resumo_diario(filtrado, float(limite))

        # Metadados do veículo
        placa = _col_first(filtrado, "Placa", selected_vehicle)
        org = _col_first(filtrado, "Organização", "—")
        serial = _col_first(filtrado, "Serial", "—")
        date_label = f"{data_inicio:%d/%m/%Y} → {data_fim:%d/%m/%Y}"

        # ── Header ───────────────────────────────────────────────
        st.markdown(
            _header_html(selected_vehicle, placa, org, serial, date_label),
            unsafe_allow_html=True,
        )

        # ── Story strip (dias recentes) ──────────────────────────
        if not resumo.empty:
            st.markdown(_story_strip_html(resumo), unsafe_allow_html=True)

        # ── Insight box ──────────────────────────────────────────
        st.markdown(
            _insight_html(kpis, resumo, filtrado, float(limite)),
            unsafe_allow_html=True,
        )

        # ── KPI cards — linha 1 ──────────────────────────────────
        vel_max = float(resumo["velocidade_maxima"].max()) if not resumo.empty else 0.0
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(kpi_card_html("Vel. Máxima Registrada", f"{vel_max:.0f}", "km/h", "orange", "orange"), unsafe_allow_html=True)
        with col2:
            st.markdown(kpi_card_html("Vel. Média em Movimento", f"{kpis['velocidade_media']:.0f}", "km/h · registros > 0", "blue", "blue"), unsafe_allow_html=True)
        with col3:
            st.markdown(kpi_card_html("Km Total", f"{kpis['total_km']:.1f}", "km percorridos", "green", "green"), unsafe_allow_html=True)

        # ── KPI cards — linha 2 ──────────────────────────────────
        col4, col5, col6 = st.columns(3)
        with col4:
            st.markdown(kpi_card_html("Alertas de Velocidade", f"{kpis['total_alertas']}", f"acima de {int(limite)} km/h", "orange", "orange"), unsafe_allow_html=True)
        with col5:
            st.markdown(kpi_card_html("Total de Paradas", f"{kpis['total_paradas']}", "eventos detectados", "muted", "white"), unsafe_allow_html=True)
        with col6:
            st.markdown(kpi_card_html("Ignição Ligada", f"{kpis['horas_ignicao_ligada']:.1f}", "horas com motor ligado", "blue", "blue"), unsafe_allow_html=True)

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        # ── Velocidade + tabela de ignição ───────────────────────
        col_vel, col_ign = st.columns([1.6, 1])
        with col_vel:
            st.plotly_chart(
                grafico_velocidade_veiculo(filtrado), use_container_width=True
            )
        with col_ign:
            st.markdown(_ignition_card(filtrado, kpis), unsafe_allow_html=True)

        # ── Distribuição + latência GPS ──────────────────────────
        col_dist, col_lat = st.columns([1.6, 1])
        with col_dist:
            st.markdown(_speed_distribution_html(filtrado), unsafe_allow_html=True)
        with col_lat:
            st.markdown(_latency_card(filtrado), unsafe_allow_html=True)

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        # ── Velocidade máxima e paradas por dia ──────────────────
        col_v, col_p = st.columns(2)
        with col_v:
            st.plotly_chart(grafico_velocidade_diaria(resumo), use_container_width=True)
        with col_p:
            st.plotly_chart(grafico_paradas_diarias(resumo), use_container_width=True)

        # ── Tabela resumo diário ─────────────────────────────────
        st.markdown("<div class='section-label'>Resumo diário</div>", unsafe_allow_html=True)
        tabela = _formatar_tabela(resumo)
        st.dataframe(tabela, use_container_width=True, hide_index=True)

        st.download_button(
            "⬇ Baixar Excel",
            data=_gerar_excel(tabela),
            file_name=f"analise_{selected_vehicle}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    except Exception as exc:
        st.error(f"Não foi possível renderizar a análise do veículo: {exc}")


# ── Helpers HTML ──────────────────────────────────────────────────────────────

def _header_html(veiculo: str, placa: str, org: str, serial: str, date_label: str) -> str:
    return f"""
    <div class="dash-header">
        <div class="dash-header-left">
            <div class="eyebrow">▸ Análise por Veículo · {org}</div>
            <h1>Veículo <span>{placa}</span></h1>
        </div>
        <div class="dash-header-right">
            <div class="status-pill">● ANÁLISE</div><br>
            {date_label}<br>
            Serial: {serial}<br>
            Cód. Veículo: {veiculo}
        </div>
    </div>
    """


def _story_strip_html(resumo: pd.DataFrame) -> str:
    recent = (
        resumo.sort_values(ROUTE_DATE_COLUMN, ascending=False)
        .head(5)
        .sort_values(ROUTE_DATE_COLUMN)
    )
    bar_colors = ["green", "blue", "orange", "green", "blue"]
    phases = []
    for i, (_, row) in enumerate(recent.iterrows()):
        try:
            date = pd.to_datetime(row[ROUTE_DATE_COLUMN]).strftime("%d/%m")
        except Exception:
            date = "—"
        km = f"{row.get('km_total', 0):.1f} km"
        vel = f"{row.get('velocidade_maxima', 0):.0f} km/h"
        try:
            inicio = pd.to_datetime(row.get("inicio")).strftime("%H:%M")
        except Exception:
            inicio = "--:--"
        try:
            fim = pd.to_datetime(row.get("fim")).strftime("%H:%M")
        except Exception:
            fim = "--:--"
        alerts = int(row.get("alertas_velocidade", 0))
        label_class = "warn" if alerts > 0 else ""
        bar_color = "orange" if alerts > 0 else bar_colors[i % len(bar_colors)]
        phases.append(f"""
        <div class="story-phase">
            <div class="phase-num">Dia {i + 1:02d}</div>
            <div class="phase-label {label_class}">{date} · {km}</div>
            <div class="phase-time">{inicio} → {fim} · pico {vel}</div>
            <div class="phase-bar {bar_color}"></div>
        </div>""")
    return f'<div class="story-strip">{"".join(phases)}</div>'


def _insight_html(kpis: dict, resumo: pd.DataFrame, df: pd.DataFrame, limite: float) -> str:
    alertas = int(kpis.get("total_alertas", 0))
    vel_max = float(resumo["velocidade_maxima"].max()) if not resumo.empty else 0.0
    total_km = float(kpis.get("total_km", 0))
    horas_lig = float(kpis.get("horas_ignicao_ligada", 0))
    paradas = int(kpis.get("total_paradas", 0))

    # Calcular tempo ocioso (ignição ligada + velocidade 0)
    try:
        ociosos = df[
            (df["Ignição"].astype(str).str.casefold() == "ligada")
            & (df["Velocidade"].astype(float) == 0)
        ]
        pct_ocioso = len(ociosos) / max(len(df), 1) * 100
    except Exception:
        pct_ocioso = 0.0

    parts = []
    is_warn = alertas > 0 or pct_ocioso > 30

    if alertas > 0:
        parts.append(f"<strong>{alertas} alertas</strong> de velocidade acima de {int(limite)} km/h.")
    if vel_max > 0:
        parts.append(f"Pico registrado: <strong>{vel_max:.0f} km/h</strong>.")
    if pct_ocioso > 10:
        parts.append(f"Veículo ficou <strong>{pct_ocioso:.0f}%</strong> do tempo ligado com velocidade 0 (ocioso).")
    if total_km > 0:
        parts.append(f"Total percorrido: <strong>{total_km:.1f} km</strong> · <strong>{horas_lig:.1f}h</strong> com motor ligado · <strong>{paradas}</strong> paradas.")

    if not parts:
        parts.append("Dados carregados com sucesso para o período selecionado.")

    icon = "⚠️" if is_warn else "📊"
    box_class = "insight-box warn" if is_warn else "insight-box"
    return f"""
    <div class="{box_class}">
        <div style="font-size:22px;flex-shrink:0;padding-top:2px">{icon}</div>
        <div class="insight-text">{" ".join(parts)}</div>
    </div>"""


def _ignition_card(df: pd.DataFrame, kpis: dict) -> str:
    try:
        ign = df["Ignição"].astype(str).str.casefold()
        n_ligada = int((ign == "ligada").sum())
        n_desligada = int((ign == "desligada").sum())
        total = max(n_ligada + n_desligada, 1)
        pct_lig = n_ligada / total * 100
        pct_des = n_desligada / total * 100

        # Ocioso: ignição ligada + vel 0
        ociosos = int(
            ((ign == "ligada") & (df["Velocidade"].astype(float) == 0)).sum()
        )
        pct_ocioso = ociosos / max(n_ligada, 1) * 100
        pct_bar = f"{min(pct_ocioso, 100):.0f}%"
    except Exception:
        n_ligada, n_desligada, pct_lig, pct_des, pct_ocioso, pct_bar = 0, 0, 0, 0, 0, "0%"

    return f"""
    <div class="kpi-card accent-orange" style="height:100%;box-sizing:border-box">
        <div class="kpi-label">Status de Ignição — Resumo</div>
        <table class="ign-table">
            <thead>
                <tr>
                    <th>Status</th><th>Registros</th><th>% Total</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><span class="ign-dot green"></span>Ligada</td>
                    <td style="color:#00e5a0">{n_ligada}</td>
                    <td style="color:#7a8099">{pct_lig:.0f}%</td>
                </tr>
                <tr>
                    <td><span class="ign-dot red"></span>Desligada</td>
                    <td style="color:#ff6b35">{n_desligada}</td>
                    <td style="color:#7a8099">{pct_des:.0f}%</td>
                </tr>
            </tbody>
        </table>
        <div style="margin-top:16px">
            <div class="kpi-label">Ignição Ligada + Vel = 0 (Ocioso)</div>
            <div style="display:flex;align-items:center;gap:10px;margin-top:6px">
                <div style="flex:1;background:#1e2229;height:8px;border-radius:4px;overflow:hidden">
                    <div style="width:{pct_bar};height:100%;background:#ff6b35;border-radius:4px"></div>
                </div>
                <span style="font-family:Space Mono,monospace;font-size:11px;color:#ff6b35;white-space:nowrap">{pct_ocioso:.0f}% ligado</span>
            </div>
        </div>
    </div>"""


def _speed_distribution_html(df: pd.DataFrame) -> str:
    try:
        vel = df["Velocidade"].astype(float)
        total = max(len(vel), 1)
        bands = [
            ("0 km/h",  int((vel == 0).sum()),          "#ff6b35", "#ff6b35"),
            ("1–20",    int(((vel > 0) & (vel <= 20)).sum()), "#4da6ff", "#4da6ff"),
            ("21–30",   int(((vel > 20) & (vel <= 30)).sum()), "#4da6ff", "#4da6ff"),
            ("31–40",   int(((vel > 30) & (vel <= 40)).sum()), "#00e5a0", "#00e5a0"),
            ("> 40",    int((vel > 40).sum()),           "#00e5a0", "#00e5a0"),
        ]
        max_count = max(b[1] for b in bands) or 1
    except Exception:
        return ""

    rows = ""
    for label, count, color, _ in bands:
        pct = count / max_count * 100
        val_color = "#ff6b35" if label == "0 km/h" else "#e8eaf0"
        rows += f"""
        <div class="hbar-row">
            <div class="hbar-label">{label}</div>
            <div class="hbar-track">
                <div class="hbar-fill" style="width:{pct:.1f}%;background:{color}"></div>
            </div>
            <div class="hbar-val" style="color:{val_color}">{count} reg</div>
        </div>"""

    return f"""
    <div class="kpi-card accent-blue">
        <div class="kpi-label">Distribuição de Velocidade</div>
        <div class="hbar-wrap" style="margin-top:12px">{rows}</div>
    </div>"""


def _latency_card(df: pd.DataFrame) -> str:
    try:
        if "Data da Gravação" not in df.columns or "Data da Coordenada" not in df.columns:
            raise ValueError("colunas ausentes")
        latency = (df["Data da Gravação"] - df["Data da Coordenada"]).dt.total_seconds() / 60
        latency = latency.clip(lower=0)
        avg_lat = float(latency.mean())
        min_lat = float(latency.min())
        max_lat = float(latency.max())
        pct_high = float((latency > 5).mean() * 100)
        fill_pct = min(avg_lat / 15 * 100, 100)
        color = "#00e5a0" if avg_lat < 3 else "#ff6b35" if avg_lat > 8 else "#4da6ff"
        conic = f"conic-gradient({color} 0% {fill_pct:.1f}%, #1e2229 {fill_pct:.1f}% 100%)"
        warning = (
            f'<span style="color:#ff6b35">⚠ {pct_high:.0f}% acima de 5 min</span>'
            if pct_high > 10
            else '<span style="color:#00e5a0">✓ Latência normal</span>'
        )
    except Exception:
        return f"""
        <div class="kpi-card accent-muted">
            <div class="kpi-label">Latência GPS Média</div>
            <div style="color:#7a8099;font-family:Space Mono,monospace;font-size:11px;margin-top:20px">
                Dados de gravação não disponíveis.
            </div>
        </div>"""

    return f"""
    <div class="kpi-card accent-muted" style="height:100%;box-sizing:border-box">
        <div class="kpi-label">Latência GPS Média</div>
        <div style="display:flex;flex-direction:column;align-items:center;padding:12px 0 8px">
            <div style="width:90px;height:90px;border-radius:50%;background:{conic};display:flex;align-items:center;justify-content:center">
                <div style="width:64px;height:64px;border-radius:50%;background:#111318;display:flex;flex-direction:column;align-items:center;justify-content:center">
                    <div style="font-family:Space Mono,monospace;font-size:16px;font-weight:700;color:{color}">~{avg_lat:.0f}</div>
                    <div style="font-family:Space Mono,monospace;font-size:8px;color:#7a8099">minutos</div>
                </div>
            </div>
            <div style="font-family:Space Mono,monospace;font-size:9px;color:#7a8099;margin-top:8px;letter-spacing:1px;text-transform:uppercase">
                Data Coord → Gravação
            </div>
        </div>
        <div style="font-family:Space Mono,monospace;font-size:9px;color:#7a8099;text-align:center;line-height:1.9">
            Mín: {min_lat:.0f} min · Máx: {max_lat:.0f} min<br>
            {warning}
        </div>
    </div>"""


# ── Tabela e Excel ────────────────────────────────────────────────────────────

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
    return tabela[["Data", "Km Total", "Vel. Máx", "Vel. Média", "Alertas", "Paradas", "Início", "Fim"]]


def _gerar_excel(tabela: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        tabela.to_excel(writer, index=False, sheet_name="Análise")
    return buffer.getvalue()


def _normalizar_periodo(periodo: object, default_start: object, max_date: object) -> tuple:
    if isinstance(periodo, (tuple, list)) and len(periodo) == 2:
        return periodo[0], periodo[1]
    return default_start, max_date


def _col_first(df: pd.DataFrame, col: str, default: str) -> str:
    try:
        return str(df[col].iloc[0])
    except Exception:
        return default


main()
