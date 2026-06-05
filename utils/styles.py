"""Estilos CSS globais do portal logístico — dark theme."""

from __future__ import annotations

import streamlit as st

_FONT_IMPORTS = """
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;800&display=swap" rel="stylesheet">
"""

_CSS = """
<style>
:root {
    --bg: #0a0c10;
    --panel: #111318;
    --border: #1e2229;
    --accent: #00e5a0;
    --warn: #ff6b35;
    --info: #4da6ff;
    --muted: #3a3f4a;
    --text: #e8eaf0;
    --sub: #7a8099;
    --mono: 'Space Mono', monospace;
    --sans: 'Syne', sans-serif;
}

/* ── Base ───────────────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: var(--sans) !important;
}

/* ── Remove Streamlit chrome ────────────────────────────── */
#MainMenu          { visibility: hidden; }
footer             { visibility: hidden; }
[data-testid="stHeader"] { display: none; }
[data-testid="stDecoration"] { display: none; }

/* ── Fundo geral ────────────────────────────────────────── */
.stApp,
body,
[data-testid="stAppViewContainer"],
[data-testid="stMainBlockContainer"],
[data-testid="stBottom"],
.main {
    background: var(--bg) !important;
}
.main .block-container {
    padding-top: 1.8rem;
    padding-bottom: 2rem;
    max-width: 1440px;
    background: var(--bg);
}

/* ── Sidebar ────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: #0d0f14 !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] * {
    color: var(--text) !important;
}
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stSlider label,
[data-testid="stSidebar"] .stDateInput label,
[data-testid="stSidebar"] .stMultiSelect label {
    color: var(--sub) !important;
    font-size: 10px !important;
    font-weight: 400 !important;
    letter-spacing: 1.5px !important;
    text-transform: uppercase !important;
    font-family: var(--mono) !important;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: var(--text) !important;
    font-family: var(--sans) !important;
}
[data-testid="stSidebar"] .stButton > button {
    background: var(--panel) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    border-radius: 6px !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    border-color: var(--accent) !important;
    color: var(--accent) !important;
}
[data-testid="stSidebarNav"] a {
    border-radius: 6px;
    padding: 6px 12px !important;
    color: var(--sub) !important;
    font-size: 13px;
    font-family: var(--sans);
}
[data-testid="stSidebarNav"] a:hover {
    background: var(--panel) !important;
    color: var(--text) !important;
}
[data-testid="stSidebarNav"] a[aria-current="page"] {
    background: rgba(0,229,160,0.12) !important;
    color: var(--accent) !important;
    font-weight: 600 !important;
    border-left: 2px solid var(--accent) !important;
}

/* ── Inputs na sidebar ──────────────────────────────────── */
[data-testid="stSidebar"] [data-baseweb="select"] > div,
[data-testid="stSidebar"] [data-baseweb="input"] > div {
    background: #16191f !important;
    border-color: var(--border) !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] span,
[data-testid="stSidebar"] [data-baseweb="input"] input {
    color: var(--text) !important;
}

/* ── Títulos ─────────────────────────────────────────────── */
h1 {
    color: var(--text) !important;
    font-weight: 800 !important;
    font-size: 1.7rem !important;
    font-family: var(--sans) !important;
    letter-spacing: -1px !important;
    padding-bottom: 0.3rem;
    border-bottom: 2px solid var(--accent) !important;
    display: inline-block;
    margin-bottom: 1.2rem !important;
}
h2, h3 {
    color: var(--text) !important;
    font-family: var(--sans) !important;
}

/* ── Metrics nativo (fallback) ───────────────────────────── */
[data-testid="metric-container"] {
    background: var(--panel) !important;
    border: 1px solid var(--border) !important;
    border-top: 2px solid var(--accent) !important;
    border-radius: 10px !important;
    padding: 16px 18px !important;
}
[data-testid="stMetricLabel"] {
    font-size: 9px !important;
    font-weight: 400 !important;
    color: var(--sub) !important;
    text-transform: uppercase !important;
    letter-spacing: 2.5px !important;
    font-family: var(--mono) !important;
}
[data-testid="stMetricValue"] {
    font-size: 2rem !important;
    font-weight: 800 !important;
    color: var(--accent) !important;
    font-family: var(--sans) !important;
    letter-spacing: -1px !important;
}
[data-testid="stMetricDelta"] {
    font-family: var(--mono) !important;
    font-size: 11px !important;
}

/* ── DataFrames ─────────────────────────────────────────── */
[data-testid="stDataFrame"] {
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    overflow: hidden !important;
    background: var(--panel) !important;
}
[data-testid="stDataFrame"] table {
    background: var(--panel) !important;
    color: var(--text) !important;
}

/* ── Botões ─────────────────────────────────────────────── */
.stButton > button {
    background: var(--panel) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    border-radius: 8px !important;
    font-family: var(--mono) !important;
    font-size: 11px !important;
    letter-spacing: 1px !important;
    transition: all .2s !important;
}
.stButton > button:hover {
    border-color: var(--accent) !important;
    color: var(--accent) !important;
    transform: translateY(-1px) !important;
}

/* ── Download button ────────────────────────────────────── */
[data-testid="stDownloadButton"] > button {
    background: rgba(0,229,160,0.08) !important;
    border: 1px solid rgba(0,229,160,0.35) !important;
    color: var(--accent) !important;
    font-family: var(--mono) !important;
    font-size: 11px !important;
    letter-spacing: 1px !important;
    border-radius: 8px !important;
}
[data-testid="stDownloadButton"] > button:hover {
    background: rgba(0,229,160,0.15) !important;
}

/* ── Alertas ─────────────────────────────────────────────── */
[data-testid="stAlert"] {
    background: rgba(255,107,53,0.07) !important;
    border: 1px solid rgba(255,107,53,0.25) !important;
    border-left: 3px solid var(--warn) !important;
    border-radius: 8px !important;
    color: var(--text) !important;
}
[data-testid="stAlert"][data-baseweb="notification"] {
    color: var(--text) !important;
}

/* ── Divisor ─────────────────────────────────────────────── */
hr { border-color: var(--border) !important; margin: 1rem 0 !important; }

/* ── Slider ─────────────────────────────────────────────── */
[data-testid="stSlider"] div[role="slider"] {
    background: var(--accent) !important;
}

/* ── Spinner ─────────────────────────────────────────────── */
[data-testid="stSpinner"] { color: var(--accent) !important; }

/* ─────────────────────────────────────────────────────────
   Componentes HTML customizados
   ───────────────────────────────────────────────────────── */

/* KPI Card */
.kpi-card {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 20px 22px;
    position: relative;
    overflow: hidden;
    margin-bottom: 2px;
}
.kpi-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
}
.kpi-card.accent-green::before  { background: #00e5a0; }
.kpi-card.accent-orange::before { background: #ff6b35; }
.kpi-card.accent-blue::before   { background: #4da6ff; }
.kpi-card.accent-muted::before  { background: #3a3f4a; }
.kpi-label {
    font-family: 'Space Mono', monospace;
    font-size: 9px;
    letter-spacing: 2.5px;
    text-transform: uppercase;
    color: #7a8099;
    margin-bottom: 10px;
}
.kpi-value {
    font-size: 36px;
    font-weight: 800;
    line-height: 1;
    letter-spacing: -1px;
    margin-bottom: 4px;
    font-family: 'Syne', sans-serif;
}
.kpi-value.green  { color: #00e5a0; }
.kpi-value.orange { color: #ff6b35; }
.kpi-value.blue   { color: #4da6ff; }
.kpi-value.white  { color: #e8eaf0; }
.kpi-sub {
    font-size: 11px;
    color: #7a8099;
    font-family: 'Space Mono', monospace;
}

/* Story Strip */
.story-strip {
    display: flex;
    gap: 0;
    margin-bottom: 20px;
    border: 1px solid #1e2229;
    border-radius: 10px;
    overflow: hidden;
}
.story-phase {
    flex: 1;
    padding: 14px 16px;
    position: relative;
    border-right: 1px solid #1e2229;
    background: #111318;
}
.story-phase:last-child { border-right: none; }
.phase-num {
    font-family: 'Space Mono', monospace;
    font-size: 9px;
    color: #3a3f4a;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 4px;
}
.phase-label {
    font-size: 13px;
    font-weight: 600;
    color: #e8eaf0;
    font-family: 'Syne', sans-serif;
    margin-bottom: 2px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.phase-label.accent { color: #00e5a0; }
.phase-label.warn   { color: #ff6b35; }
.phase-time {
    font-family: 'Space Mono', monospace;
    font-size: 10px;
    color: #7a8099;
}
.phase-bar {
    position: absolute;
    bottom: 0; left: 0; right: 0;
    height: 3px;
    background: #3a3f4a;
}
.phase-bar.green  { background: #00e5a0; }
.phase-bar.orange { background: #ff6b35; }
.phase-bar.blue   { background: #4da6ff; }

/* Insight Box */
.insight-box {
    background: rgba(0,229,160,0.06);
    border: 1px solid rgba(0,229,160,0.2);
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 16px;
    display: flex;
    align-items: flex-start;
    gap: 14px;
}
.insight-box.warn {
    background: rgba(255,107,53,0.06);
    border-color: rgba(255,107,53,0.2);
}
.insight-text {
    font-size: 13px;
    line-height: 1.7;
    color: #c0e8d8;
    font-family: 'Syne', sans-serif;
}
.insight-box.warn .insight-text { color: #f0cfc0; }
.insight-text strong { color: #00e5a0; font-weight: 600; }
.insight-box.warn .insight-text strong { color: #ff6b35; }

/* Section header */
.section-label {
    font-family: 'Space Mono', monospace;
    font-size: 9px;
    letter-spacing: 2.5px;
    text-transform: uppercase;
    color: #7a8099;
    margin: 20px 0 10px;
    padding-bottom: 6px;
    border-bottom: 1px solid #1e2229;
}

/* Horizontal speed bars */
.hbar-wrap { padding: 4px 0; }
.hbar-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 10px;
}
.hbar-label {
    font-family: 'Space Mono', monospace;
    font-size: 10px;
    color: #7a8099;
    width: 56px;
    text-align: right;
    flex-shrink: 0;
}
.hbar-track {
    flex: 1;
    height: 8px;
    background: #1e2229;
    border-radius: 4px;
    overflow: hidden;
}
.hbar-fill { height: 100%; border-radius: 4px; }
.hbar-val {
    font-family: 'Space Mono', monospace;
    font-size: 10px;
    color: #e8eaf0;
    width: 44px;
    text-align: right;
}

/* Dashboard section card */
.section-card {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 18px 20px;
    margin-bottom: 4px;
}
.section-card-title {
    font-family: 'Space Mono', monospace;
    font-size: 9px;
    letter-spacing: 2.5px;
    text-transform: uppercase;
    color: #7a8099;
    margin-bottom: 14px;
}

/* Header customizado */
.dash-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    margin-bottom: 28px;
    padding-bottom: 20px;
    border-bottom: 1px solid #1e2229;
}
.dash-header-left .eyebrow {
    font-family: 'Space Mono', monospace;
    font-size: 10px;
    letter-spacing: 3px;
    color: #00e5a0;
    text-transform: uppercase;
    margin-bottom: 6px;
}
.dash-header-left h1 {
    font-size: 32px !important;
    font-weight: 800 !important;
    letter-spacing: -1px !important;
    border: none !important;
    margin-bottom: 0 !important;
    padding-bottom: 0 !important;
    display: block !important;
    line-height: 1 !important;
}
.dash-header-left h1 span { color: #00e5a0; }
.dash-header-right {
    text-align: right;
    font-family: 'Space Mono', monospace;
    font-size: 11px;
    color: #7a8099;
    line-height: 1.8;
}
.status-pill {
    display: inline-block;
    background: rgba(0,229,160,0.12);
    color: #00e5a0;
    border: 1px solid rgba(0,229,160,0.3);
    border-radius: 4px;
    padding: 3px 10px;
    font-size: 10px;
    letter-spacing: 2px;
    margin-bottom: 6px;
}
.status-pill.orange {
    background: rgba(255,107,53,0.12);
    color: #ff6b35;
    border-color: rgba(255,107,53,0.3);
}

/* Ignition table */
.ign-table { width: 100%; border-collapse: collapse; margin-top: 10px; }
.ign-table th {
    font-family: 'Space Mono', monospace;
    font-size: 9px;
    letter-spacing: 2px;
    color: #7a8099;
    text-transform: uppercase;
    padding: 0 0 10px 0;
    text-align: left;
    border-bottom: 1px solid #1e2229;
}
.ign-table td {
    font-family: 'Space Mono', monospace;
    font-size: 11px;
    padding: 8px 0;
    border-bottom: 1px solid rgba(30,34,41,0.6);
    vertical-align: middle;
}
.ign-table tr:last-child td { border-bottom: none; }
.ign-dot {
    width: 7px; height: 7px;
    border-radius: 50%;
    display: inline-block;
    margin-right: 6px;
    vertical-align: middle;
}
.ign-dot.green { background: #00e5a0; box-shadow: 0 0 5px #00e5a0; }
.ign-dot.red   { background: #ff6b35; box-shadow: 0 0 5px #ff6b35; }

</style>
"""


def aplicar_estilos() -> None:
    """Injeta fontes e CSS global na página atual do Streamlit."""
    st.markdown(_FONT_IMPORTS, unsafe_allow_html=True)
    st.markdown(_CSS, unsafe_allow_html=True)
