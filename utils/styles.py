"""Estilos CSS globais do portal logístico."""

from __future__ import annotations

import streamlit as st

_CSS = """
<style>

/* ── Fonte base ─────────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: 'Inter', 'Segoe UI', sans-serif;
}

/* ── Remove rodapé e menu hamburger do Streamlit ────────── */
#MainMenu          { visibility: hidden; }
footer             { visibility: hidden; }
[data-testid="stHeader"] { display: none; }

/* ── Sidebar escura ─────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: #0f172a !important;
    border-right: 1px solid #1e293b;
}
[data-testid="stSidebar"] * {
    color: #cbd5e1 !important;
}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stSlider label,
[data-testid="stSidebar"] .stDateInput label,
[data-testid="stSidebar"] .stMultiSelect label,
[data-testid="stSidebar"] .stToggle label {
    color: #94a3b8 !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    text-transform: uppercase;
    letter-spacing: .4px;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: #f1f5f9 !important;
}
[data-testid="stSidebar"] .stButton > button {
    background: #1e293b;
    border: 1px solid #334155;
    color: #e2e8f0 !important;
    border-radius: 6px;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: #334155;
    border-color: #475569;
}

/* ── Área principal ─────────────────────────────────────── */
[data-testid="stAppViewContainer"] {
    background: #f8fafc;
}
.main .block-container {
    padding-top: 1.5rem;
    padding-bottom: 2rem;
    max-width: 1400px;
}

/* ── Títulos ─────────────────────────────────────────────── */
h1 {
    color: #0f172a !important;
    font-weight: 700 !important;
    font-size: 1.7rem !important;
    letter-spacing: -.3px;
    padding-bottom: 0.3rem;
    border-bottom: 3px solid #3b82f6;
    display: inline-block;
    margin-bottom: 1.2rem !important;
}
h2, h3 {
    color: #1e293b !important;
    font-weight: 600 !important;
}

/* ── Cards de métricas ───────────────────────────────────── */
[data-testid="metric-container"] {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 14px 16px !important;
    box-shadow: 0 1px 4px rgba(0,0,0,.06);
    transition: box-shadow .2s;
}
[data-testid="metric-container"]:hover {
    box-shadow: 0 4px 12px rgba(0,0,0,.10);
}
[data-testid="stMetricLabel"] {
    font-size: 12px !important;
    font-weight: 600 !important;
    color: #64748b !important;
    text-transform: uppercase;
    letter-spacing: .4px;
}
[data-testid="stMetricValue"] {
    font-size: 1.5rem !important;
    font-weight: 700 !important;
    color: #0f172a !important;
}

/* ── Tabelas / dataframes ───────────────────────────────── */
[data-testid="stDataFrame"] {
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 1px 4px rgba(0,0,0,.05);
}

/* ── Botões principais ───────────────────────────────────── */
.stButton > button {
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    transition: all .2s !important;
}
.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(59,130,246,.25) !important;
}

/* ── Alertas / info / success ───────────────────────────── */
[data-testid="stAlert"] {
    border-radius: 8px !important;
    border-left-width: 4px !important;
}

/* ── Divisor ─────────────────────────────────────────────── */
hr {
    border-color: #e2e8f0 !important;
    margin: 1rem 0 !important;
}

/* ── Sliders na sidebar ─────────────────────────────────── */
[data-testid="stSidebar"] [data-testid="stSlider"] div[role="slider"] {
    background: #3b82f6 !important;
}

/* ── Navegação entre páginas ────────────────────────────── */
[data-testid="stSidebarNav"] a {
    border-radius: 6px;
    padding: 6px 12px !important;
    color: #94a3b8 !important;
    font-size: 14px;
}
[data-testid="stSidebarNav"] a:hover {
    background: #1e293b !important;
    color: #f1f5f9 !important;
}
[data-testid="stSidebarNav"] a[aria-current="page"] {
    background: #1d4ed8 !important;
    color: #ffffff !important;
    font-weight: 600 !important;
}

</style>
"""


def aplicar_estilos() -> None:
    """Injeta o CSS global na página atual do Streamlit."""
    st.markdown(_CSS, unsafe_allow_html=True)
