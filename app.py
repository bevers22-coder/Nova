
import json
import hmac
import os
import xml.etree.ElementTree as ET
from datetime import datetime
from html import escape
from pathlib import Path
from urllib.parse import quote
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf

from modules.backtesting import VeyroBacktester
from modules.document_tools import EXPORTS, export_document
from modules.portfolio import calculate_portfolio_analytics
from modules.screener import apply_screener_filters
from modules.storage import (
    add_to_watchlist,
    get_app_setting,
    get_holdings as load_persisted_holdings,
    get_saved_documents,
    get_watchlist,
    initialize_storage,
    normalize_ticker,
    remove_from_watchlist,
    remove_holding,
    save_document,
    save_holding,
    set_app_setting,
)
from modules.study_inputs import read_study_upload
from modules.voice_commands import parse_voice_command

# -----------------------------------------
# NOVA — MARKET INTELLIGENCE
# -----------------------------------------

st.set_page_config(
    page_title="Nova | Market Intelligence",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="collapsed"
)

access_password = os.environ.get("NOVA_ACCESS_PASSWORD", "").strip()
try:
    access_password = access_password or str(
        st.secrets.get("NOVA_ACCESS_PASSWORD", "")
    ).strip()
except (FileNotFoundError, AttributeError):
    pass

if not access_password:
    st.error(
        "NOVA is locked until a private access password is configured. "
        "Set NOVA_ACCESS_PASSWORD in the server environment or Streamlit secrets."
    )
    st.code(
        "export NOVA_ACCESS_PASSWORD='your-private-password'\n"
        "streamlit run app.py",
        language="bash",
    )
    st.stop()

if access_password:
    if not st.session_state.get("nova_authenticated"):
        st.title("NOVA / SECURE ACCESS")
        entered_password = st.text_input("Access password", type="password")
        if st.button("UNLOCK NOVA", type="primary"):
            if hmac.compare_digest(entered_password, access_password):
                st.session_state.nova_authenticated = True
                st.rerun()
            else:
                st.error("Access denied.")
        st.stop()

try:
    initialize_storage()
except (OSError, ValueError) as error:
    st.error(f"Nova's private local storage could not be opened: {error}")
    st.stop()

voice_component = components.declare_component(
    "nova_voice",
    path=str(Path(__file__).parent / "voice_component")
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&family=Rajdhani:wght@500;600;700&display=swap');
:root {
    --nova-cyan: #42d7ff;
    --nova-blue: #167fe8;
    --nova-violet: #845cff;
    --nova-muted: #8ea8c2;
    --nova-line: rgba(100, 177, 235, .28);
    --nova-panel: rgba(4, 9, 17, .9);
}
[data-testid="stButton"] button[kind="primary"] {
    color: #06101a;
    background: linear-gradient(110deg, #63cfff, #8b78ff);
    border-color: #c3dfff;
    box-shadow: 0 0 18px rgba(66, 180, 255, .25);
}
.stApp {
    position: relative;
    isolation: isolate;
    background:
        radial-gradient(ellipse at 50% 42%, rgba(21, 107, 181, .19), transparent 39%),
        radial-gradient(ellipse at 50% 42%, rgba(3, 7, 13, .04), #03060a 77%),
        linear-gradient(rgba(116, 164, 203, .025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(116, 164, 203, .025) 1px, transparent 1px),
        #03060a;
    background-size: auto, auto, 36px 36px, 36px 36px, auto;
    color: #d7e8f7;
    font-family: 'IBM Plex Mono', monospace;
}
.stApp [data-testid="stAppViewContainer"], .stApp > header {
    position: relative;
    z-index: 1;
}
.stApp::before, .stApp::after {
    position: fixed;
    inset: 0;
    z-index: 0;
    pointer-events: none;
    content: "";
}
.stApp::before {
    opacity: .5;
    background:
        radial-gradient(circle at 50% 43%, transparent 0 17.8%, rgba(78, 196, 255, .36) 18%, rgba(78, 196, 255, .08) 18.2%, transparent 18.55%),
        radial-gradient(circle at 50% 43%, transparent 0 21.3%, rgba(187, 206, 225, .24) 21.45%, transparent 21.7% 24.7%, rgba(100, 157, 208, .22) 24.85%, transparent 25.05%),
        repeating-conic-gradient(from 2deg at 50% 43%, transparent 0 8deg, rgba(120, 194, 238, .13) 8.15deg 8.35deg, transparent 8.5deg 16deg),
        radial-gradient(circle at 13% 24%, #42d7ff 0 1px, transparent 2px),
        radial-gradient(circle at 77% 63%, #42d7ff 0 1px, transparent 2px),
        radial-gradient(circle at 44% 82%, #845cff 0 1px, transparent 2px),
        linear-gradient(115deg, transparent 47%, rgba(91, 174, 231, .045) 48%, transparent 49%);
    background-size: auto, auto, auto, 173px 151px, 211px 187px, 139px 197px, 100% 100%;
    animation: nova-drift 32s linear infinite;
}
.stApp::after {
    opacity: .2;
    background:
        repeating-linear-gradient(0deg, transparent 0 5px, rgba(120, 170, 212, .025) 6px, transparent 7px),
        linear-gradient(90deg, transparent 4%, var(--nova-blue) 13%, var(--nova-violet) 87%, transparent 96%);
    background-size: auto, 100% 2px;
    background-position: 0 0, 0 100%;
    background-repeat: repeat, no-repeat;
}
[data-testid="stSidebar"], [data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"] {
    display: none !important;
}
h1, h2, h3, h4 {
    color: #d8fdff !important;
    letter-spacing: .07em;
    font-family: 'Rajdhani', sans-serif !important;
    text-transform: uppercase;
    text-shadow: 0 0 18px rgba(8, 245, 239, .14);
}
[data-testid="stCaptionContainer"] {
    color: var(--nova-muted);
}
div[data-testid="stMetric"] {
    background: linear-gradient(145deg, rgba(13, 26, 42, .94), rgba(5, 9, 16, .97));
    border: 1px solid var(--nova-line);
    border-radius: 2px;
    padding: 14px 16px;
    box-shadow: inset 0 1px 0 rgba(150, 233, 245, .05), 0 0 16px rgba(8, 245, 239, .035);
}
[data-testid="stMetricLabel"] {
    color: #9eb4c9;
    text-transform: uppercase;
    letter-spacing: .13em;
    font-size: .68rem;
}
[data-testid="stMetricValue"] {
    color: var(--nova-cyan);
    font-family: 'Rajdhani', sans-serif;
}
.stButton button {
    background: linear-gradient(110deg, #0b1c2d, #151328);
    color: #e2f1ff;
    border: 1px solid #357fba;
    border-radius: 1px;
    letter-spacing: .10em;
    font-family: 'IBM Plex Mono', monospace;
    box-shadow: inset 0 0 14px rgba(8, 245, 239, .04);
}
.stButton button:hover {
    background: #102e4b;
    border-color: var(--nova-cyan);
    color: white;
    box-shadow: 0 0 18px rgba(8, 245, 239, .2);
}
[data-testid="stDataFrame"] {
    border: 1px solid var(--nova-line);
}
div[data-testid="stAlert"] {
    border-radius: 1px;
}
[data-testid="stTextInput"] input, [data-testid="stNumberInput"] input {
    background: #06141c;
    border-color: var(--nova-line);
    color: #dcfeff;
}
[data-testid="stSelectbox"] [data-baseweb="select"] > div {
    background: #06141c;
    border-color: var(--nova-line);
}
[data-testid="stTabs"] button {
    color: var(--nova-muted);
}
[data-testid="stTabs"] button[aria-selected="true"] {
    color: var(--nova-cyan);
    border-bottom-color: var(--nova-cyan);
}
[data-testid="stExpander"] {
    border-color: var(--nova-line);
    border-radius: 1px;
}
hr {
    border-color: rgba(100, 177, 235, .2);
}
.nova-eyebrow {
    color: var(--nova-cyan);
    font-size: .76rem;
    letter-spacing: .18em;
    text-transform: uppercase;
}
.nova-panel {
    border: 1px solid var(--nova-line);
    border-left: 3px solid var(--nova-cyan);
    padding: 18px 20px;
    background: linear-gradient(110deg, rgba(4, 33, 43, .92), rgba(3, 15, 23, .86));
    margin: 8px 0 22px;
    box-shadow: inset 0 0 32px rgba(8, 245, 239, .025);
}
.nova-hud-strip {
    color: var(--nova-cyan);
    font: 600 .72rem 'IBM Plex Mono', monospace;
    letter-spacing: .11em;
    padding: 7px 10px;
    border-top: 1px solid var(--nova-line);
    border-bottom: 1px solid var(--nova-line);
    background: rgba(4, 28, 38, .55);
}
.nova-time {
    color: var(--nova-cyan);
    font: 700 2.2rem 'Rajdhani', sans-serif;
    line-height: 1.05;
}
.nova-weather-temp {
    color: #e1feff;
    font: 700 2rem 'Rajdhani', sans-serif;
}
.nova-orbit-wrap {
    display: grid;
    place-items: center;
    min-height: 250px;
    overflow: hidden;
    border: 1px solid var(--nova-line);
    background: radial-gradient(circle, rgba(8, 245, 239, .10), rgba(3, 14, 21, .5) 52%, transparent 72%);
}
.nova-reactor {
    position: relative;
    display: grid;
    place-items: center;
    width: 220px;
    height: 220px;
    border: 1px solid rgba(8,245,239,.55);
    border-radius: 50%;
    background: repeating-conic-gradient(from 4deg, rgba(8,245,239,.72) 0 1deg, transparent 1deg 12deg);
    box-shadow: 0 0 30px rgba(8,245,239,.18), inset 0 0 25px rgba(8,245,239,.1);
    animation: nova-spin 36s linear infinite;
}
.nova-reactor::before, .nova-reactor::after {
    position: absolute;
    content: "";
    border: 1px solid rgba(8,245,239,.55);
    border-radius: 50%;
}
.nova-reactor::before {
    inset: 15px;
    border-style: dashed;
    animation: nova-spin 22s linear infinite reverse;
}
.nova-reactor::after {
    inset: 38px;
    border-width: 3px;
    box-shadow: 0 0 24px rgba(8,245,239,.28), inset 0 0 20px rgba(8,245,239,.16);
}
.nova-reactor-core {
    z-index: 1;
    display: grid;
    place-items: center;
    width: 92px;
    height: 92px;
    border: 1px solid var(--nova-cyan);
    border-radius: 50%;
    color: #d8fdff;
    background: radial-gradient(circle, rgba(8,245,239,.5), rgba(3,17,26,.95) 72%);
    font: 700 1rem 'Rajdhani', sans-serif;
    letter-spacing: .14em;
    text-shadow: 0 0 14px var(--nova-cyan);
    animation: nova-pulse 3s ease-in-out infinite;
}
.nova-reactor-label {
    position: absolute;
    color: var(--nova-cyan);
    font: 600 .58rem 'IBM Plex Mono', monospace;
    letter-spacing: .12em;
    animation: nova-counter-spin 36s linear infinite;
}
.nova-reactor-label.top { top: 8px; }
.nova-reactor-label.bottom { bottom: 8px; }
.nova-node {
    min-height: 120px;
    padding: 16px;
    border-left: 2px solid var(--nova-cyan);
    background: linear-gradient(90deg, rgba(4, 33, 43, .8), transparent);
    color: #b6e5e9;
    font-size: .78rem;
    line-height: 1.8;
}
.nova-node strong {
    color: var(--nova-cyan);
    font-size: .68rem;
    letter-spacing: .12em;
}
.nova-terminal-bar {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    padding: 8px 12px;
    border: 1px solid var(--nova-line);
    border-bottom: 0;
    color: var(--nova-muted);
    background: rgba(3, 18, 27, .72);
    font-size: .68rem;
    letter-spacing: .12em;
    text-transform: uppercase;
}
.nova-terminal-bar strong {
    color: var(--nova-cyan);
    font-weight: 600;
}
.nova-headline-rail {
    overflow: hidden;
    margin: 12px 0;
    border: 1px solid var(--nova-line);
    background: rgba(3, 18, 27, .88);
    color: #d8fdff;
    white-space: nowrap;
}
.nova-headline-track {
    display: flex;
    width: max-content;
    animation: nova-marquee 54s linear infinite;
}
.nova-headline-track span {
    display: inline-block;
    padding: 10px 24px;
    color: var(--nova-cyan);
    font-size: .72rem;
    letter-spacing: .08em;
}
.nova-headline-track:hover {
    animation-play-state: paused;
}
.nova-headline-card {
    display: block;
    margin: 8px 0;
    padding: 10px 12px;
    border-left: 2px solid var(--nova-cyan);
    background: rgba(4, 25, 34, .7);
    color: #d8fdff !important;
    font-size: .75rem;
    line-height: 1.6;
    text-decoration: none !important;
}
.nova-headline-card:hover {
    background: rgba(8, 70, 79, .55);
    box-shadow: 0 0 14px rgba(8, 245, 239, .10);
}
.nova-headline-meta {
    display: block;
    margin-top: 4px;
    color: var(--nova-muted);
    font-size: .62rem;
    letter-spacing: .07em;
}
.nova-spectrum {
    display: flex;
    align-items: center;
    gap: 3px;
    height: 34px;
    padding: 0 10px;
    border-left: 1px solid var(--nova-line);
}
.nova-spectrum span {
    width: 3px;
    height: 5px;
    background: var(--nova-cyan);
    box-shadow: 0 0 8px rgba(8, 245, 239, .45);
    animation: nova-spectrum 1.1s ease-in-out infinite;
}
.nova-spectrum span:nth-child(3n) { animation-delay: -.35s; }
.nova-spectrum span:nth-child(2n) { animation-delay: -.7s; }
.nova-command-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
    margin: 0 0 10px;
    padding: 10px 14px;
    border: 1px solid var(--nova-line);
    background: linear-gradient(110deg, rgba(4, 33, 43, .95), rgba(3, 15, 23, .95));
}
.nova-command-brand {
    color: #d8fdff;
    font: 700 1.05rem 'Rajdhani', sans-serif;
    letter-spacing: .16em;
}
.nova-command-brand span {
    color: var(--nova-cyan);
}
.nova-nav-label {
    margin: 5px 0 7px;
    color: var(--nova-muted);
    font-size: .62rem;
    letter-spacing: .15em;
}
.st-key-nova-nav-console [class*="st-key-nav_"] {
    display: flex;
    justify-content: center;
}
.st-key-nova-nav-console [class*="st-key-nav_"] button {
    width: 116px;
    min-width: 116px;
    height: 116px;
    min-height: 116px;
    padding: 12px;
    border-radius: 50%;
    border: 1px solid rgba(66, 215, 255, .72);
    color: #bff7ff;
    background:
        radial-gradient(circle, rgba(28, 102, 143, .34), rgba(3, 14, 23, .95) 72%);
    box-shadow: inset 0 0 22px rgba(66, 215, 255, .08), 0 0 14px rgba(66, 215, 255, .12);
    font: 600 .68rem 'IBM Plex Mono', monospace;
    letter-spacing: .08em;
    white-space: pre-line;
    transition: transform .24s ease, box-shadow .24s ease, border-color .24s ease;
}
.st-key-nova-nav-console [class*="st-key-nav_"] button:hover {
    transform: scale(1.06);
    border-color: #bff7ff;
    box-shadow: inset 0 0 25px rgba(66, 215, 255, .17), 0 0 25px rgba(66, 215, 255, .3);
}
.st-key-nova-nav-console [class*="st-key-nav_"] button[kind="primary"] {
    color: #031019;
    border-color: #bff7ff;
    background: radial-gradient(circle, #71eaff, #1689bb 80%);
    box-shadow: 0 0 26px rgba(66, 215, 255, .42);
}
.nova-nav-reactor {
    display: grid;
    min-height: 130px;
    place-items: center;
}
.nova-nav-reactor .nova-reactor {
    width: 128px;
    height: 128px;
}
.nova-nav-reactor .nova-reactor::before { inset: 9px; }
.nova-nav-reactor .nova-reactor::after { inset: 24px; }
.nova-nav-reactor .nova-reactor-core {
    width: 60px;
    height: 60px;
    font-size: .78rem;
}
.nova-nav-reactor .nova-reactor-label {
    font-size: .43rem;
}
.nova-nav-reactor .nova-reactor-label.top { top: 4px; }
.nova-nav-reactor .nova-reactor-label.bottom { bottom: 4px; }
.nova-radar-display {
    position: relative;
    width: min(460px, 100%);
    aspect-ratio: 1;
    margin: 18px auto;
    overflow: hidden;
    border: 1px solid rgba(66, 215, 255, .55);
    border-radius: 50%;
    background:
        radial-gradient(circle, transparent 0 23%, rgba(66, 215, 255, .45) 23.2%, transparent 23.6% 48%, rgba(66, 215, 255, .4) 48.2%, transparent 48.6% 73%, rgba(66, 215, 255, .35) 73.2%, transparent 73.6%),
        linear-gradient(90deg, transparent 49.8%, rgba(66, 215, 255, .28) 50%, transparent 50.2%),
        linear-gradient(transparent 49.8%, rgba(66, 215, 255, .28) 50%, transparent 50.2%),
        radial-gradient(circle, rgba(5, 37, 46, .95), rgba(2, 9, 15, .96));
    box-shadow: inset 0 0 32px rgba(66, 215, 255, .12), 0 0 24px rgba(66, 215, 255, .08);
}
.nova-radar-display::after {
    position: absolute;
    inset: 0;
    border-radius: 50%;
    background: conic-gradient(from 0deg, transparent 0 300deg, rgba(66, 215, 255, .02) 330deg, rgba(66, 215, 255, .22) 358deg, transparent 360deg);
    content: "";
    animation: nova-spin 8s linear infinite;
}
.nova-radar-crosshair {
    position: absolute;
    inset: 10%;
    z-index: 1;
    border: 1px dashed rgba(66, 215, 255, .14);
    border-radius: 50%;
    pointer-events: none;
}
.nova-radar-point {
    position: absolute;
    z-index: 2;
    display: grid;
    width: 40px;
    height: 40px;
    place-items: center;
    transform: translate(-50%, -50%);
    border: 1px solid #9af4ff;
    border-radius: 50%;
    color: #d8fdff;
    background: rgba(5, 30, 43, .9);
    box-shadow: 0 0 16px rgba(66, 215, 255, .7);
    font: 600 .55rem 'IBM Plex Mono', monospace;
    animation: nova-pulse 2.8s ease-in-out infinite;
}
.nova-school-note {
    border: 1px solid var(--nova-line);
    border-left: 3px solid var(--nova-cyan);
    padding: 12px 14px;
    background: rgba(4, 25, 34, .72);
    color: #b6e5e9;
    font-size: .78rem;
    line-height: 1.7;
}
.nova-console-panel {
    min-height: 250px;
    padding: 16px;
    border: 1px solid var(--nova-line);
    background: linear-gradient(150deg, rgba(4, 25, 34, .94), rgba(2, 11, 17, .92));
    box-shadow: inset 0 0 24px rgba(8, 245, 239, .025);
}
.nova-console-title {
    margin-bottom: 14px;
    color: var(--nova-cyan);
    font-size: .7rem;
    letter-spacing: .14em;
    text-transform: uppercase;
}
.nova-console-row {
    display: flex;
    justify-content: space-between;
    gap: 10px;
    padding: 9px 0;
    border-top: 1px solid rgba(8, 245, 239, .12);
    color: #a7d8de;
    font-size: .72rem;
}
.nova-console-row strong {
    color: #d8fdff;
    font-weight: 500;
    text-align: right;
}
.nova-console-note {
    margin-top: 12px;
    color: var(--nova-muted);
    font-size: .66rem;
    line-height: 1.7;
}
.nova-watchlist {
    min-height: 54px;
    padding: 10px 0;
    border-top: 1px solid rgba(8, 245, 239, .12);
    color: #d8fdff;
    font-size: .72rem;
    line-height: 1.8;
    overflow-wrap: anywhere;
}
.nova-orbit-wrap {
    min-height: 250px;
}
@media (max-width: 760px) {
    .nova-console-panel {
        min-height: 0;
    }
    .nova-terminal-bar {
        flex-wrap: wrap;
    }
    .nova-reactor {
        width: 190px;
        height: 190px;
    }
    .st-key-nova-nav-console [class*="st-key-nav_"] button {
        width: 88px;
        min-width: 88px;
        height: 88px;
        min-height: 88px;
        padding: 8px;
        font-size: .58rem;
    }
}
@keyframes nova-spin {
    to { transform: rotate(360deg); }
}
@keyframes nova-counter-spin {
    to { transform: rotate(-360deg); }
}
@keyframes nova-drift {
    to {
        background-position:
            0 0, 0 0, 0 0,
            173px 151px, -211px -187px, 139px -197px, 0 0;
    }
}
@keyframes nova-pulse {
    50% { box-shadow: 0 0 30px rgba(8,245,239,.58), inset 0 0 22px rgba(8,245,239,.28); }
}
@keyframes nova-marquee {
    to { transform: translateX(-50%); }
}
@keyframes nova-spectrum {
    0%, 100% { height: 5px; opacity: .48; }
    50% { height: 28px; opacity: 1; }
}
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation-duration: .01ms !important;
        animation-iteration-count: 1 !important;
    }
    .nova-headline-rail { overflow-x: auto; }
}
.nova-small {
    color: var(--nova-muted);
    font-size: .72rem;
    letter-spacing: .06em;
    text-transform: uppercase;
}
.st-key-portfolio-dashboard {
    --portfolio-blue: #63a8ff;
    padding: 18px;
    border: 1px solid rgba(99, 168, 255, .34);
    background:
        radial-gradient(ellipse at 100% 0%, rgba(147, 91, 255, .15), transparent 38%),
        linear-gradient(145deg, rgba(5, 20, 43, .9), rgba(15, 11, 35, .9));
    box-shadow: inset 0 0 32px rgba(99, 168, 255, .035), 0 0 24px rgba(99, 168, 255, .04);
}
.st-key-portfolio-dashboard h1,
.st-key-portfolio-dashboard h2,
.st-key-portfolio-dashboard h3 {
    color: #dce8ff !important;
    text-shadow: 0 0 18px rgba(147, 91, 255, .2);
}
.st-key-portfolio-dashboard .nova-eyebrow,
.st-key-portfolio-dashboard [data-testid="stMetricValue"] {
    color: var(--portfolio-blue);
}
.st-key-portfolio-dashboard [data-testid="stMetric"] {
    border-color: rgba(147, 91, 255, .34);
    background: linear-gradient(145deg, rgba(11, 29, 59, .96), rgba(22, 14, 46, .96));
    box-shadow: inset 0 1px 0 rgba(178, 138, 255, .07), 0 0 16px rgba(99, 168, 255, .04);
}
.st-key-portfolio-dashboard [data-testid="stMetricLabel"] {
    color: #a7b9df;
}
.st-key-portfolio-dashboard [data-testid="stDataFrame"] {
    border-color: rgba(99, 168, 255, .32);
}
</style>
""", unsafe_allow_html=True)

if get_app_setting("reduce_motion", "0") == "1":
    st.markdown(
        "<style>*,*::before,*::after{animation-duration:.01ms!important;"
        "animation-iteration-count:1!important;transition-duration:.01ms!important}</style>",
        unsafe_allow_html=True,
    )

# -----------------------------------------
# DATA FUNCTIONS
# -----------------------------------------

@st.cache_data(ttl=300)
def get_stock_data(ticker, period="5y"):
    data = yf.download(
        ticker,
        period=period,
        auto_adjust=True,
        progress=False
    )

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    if data.empty or "Close" not in data.columns:
        return pd.DataFrame()

    data["Returns"] = data["Close"].pct_change()
    data["SMA20"] = data["Close"].rolling(20).mean()
    data["SMA50"] = data["Close"].rolling(50).mean()
    data["SMA200"] = data["Close"].rolling(200).mean()
    data["EMA20"] = data["Close"].ewm(span=20, adjust=False).mean()
    data["EMA50"] = data["Close"].ewm(span=50, adjust=False).mean()
    data["BB_Middle"] = data["Close"].rolling(20).mean()
    data["BB_Std"] = data["Close"].rolling(20).std()
    data["BB_Upper"] = data["BB_Middle"] + 2 * data["BB_Std"]
    data["BB_Lower"] = data["BB_Middle"] - 2 * data["BB_Std"]
    data["MACD"] = data["Close"].ewm(span=12, adjust=False).mean() - data["Close"].ewm(span=26, adjust=False).mean()
    data["MACD_Signal"] = data["MACD"].ewm(span=9, adjust=False).mean()
    data["MACD_Histogram"] = data["MACD"] - data["MACD_Signal"]
    data["Volatility"] = data["Returns"].rolling(20).std() * np.sqrt(252)
    delta = data["Close"].diff()
    average_gain = delta.clip(lower=0).rolling(14).mean()
    average_loss = -delta.clip(upper=0).rolling(14).mean()
    relative_strength = average_gain / average_loss.replace(0, np.nan)
    data["RSI14"] = 100 - (100 / (1 + relative_strength))
    data.loc[(average_loss == 0) & (average_gain > 0), "RSI14"] = 100
    data.loc[(average_loss == 0) & (average_gain == 0), "RSI14"] = 50
    data["AverageVolume20"] = data["Volume"].rolling(20).mean()

    return data.dropna(subset=["Close"])


@st.cache_data(ttl=60, show_spinner=False)
def get_market_indices():
    symbols = {
        "S&P 500": "^GSPC",
        "Nasdaq Composite": "^IXIC",
        "Dow Jones": "^DJI",
        "Russell 2000": "^RUT",
    }
    data = yf.download(
        list(symbols.values()),
        period="5d",
        interval="1d",
        auto_adjust=False,
        progress=False,
        group_by="column",
        threads=False,
        timeout=15,
    )
    if data.empty:
        return {}
    if isinstance(data.columns, pd.MultiIndex):
        if "Close" in data.columns.get_level_values(0):
            close = data["Close"]
        elif "Close" in data.columns.get_level_values(1):
            close = data.xs("Close", axis=1, level=1)
        else:
            return {}
    elif "Close" in data:
        close = data[["Close"]].rename(columns={"Close": symbols["S&P 500"]})
    else:
        return {}
    if isinstance(close, pd.Series):
        close = close.to_frame()
    snapshot = {}
    for label, ticker in symbols.items():
        if ticker not in close:
            continue
        prices = close[ticker].dropna()
        if prices.empty:
            continue
        previous = float(prices.iloc[-2]) if len(prices) > 1 else None
        latest = float(prices.iloc[-1])
        snapshot[label] = {
            "ticker": ticker,
            "price": latest,
            "change_pct": (
                (latest / previous - 1) * 100
                if previous is not None and previous else None
            ),
            "as_of": pd.Timestamp(prices.index[-1]),
        }
    return snapshot


def get_us_market_schedule_status():
    current = datetime.now(ZoneInfo("America/New_York"))
    minute_of_day = current.hour * 60 + current.minute
    if current.weekday() >= 5:
        return "CLOSED", current
    if 9 * 60 + 30 <= minute_of_day < 16 * 60:
        return "REGULAR HOURS", current
    if 4 * 60 <= minute_of_day < 9 * 60 + 30:
        return "PRE-MARKET", current
    if 16 * 60 <= minute_of_day < 20 * 60:
        return "AFTER-HOURS", current
    return "CLOSED", current


@st.cache_data(ttl=300)
def get_chart_data(ticker, period):
    range_settings = {
        "1d": ("1d", "5m"),
        "1w": ("5d", "15m"),
        "1mo": ("1mo", "1d"),
        "3mo": ("3mo", "1d"),
        "6mo": ("6mo", "1d"),
        "1y": ("1y", "1d"),
        "5y": ("5y", "1d"),
    }
    data_period, interval = range_settings[period]
    data = yf.download(
        ticker,
        period=data_period,
        interval=interval,
        auto_adjust=True,
        progress=False,
        timeout=15,
    )
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    if data.empty or "Close" not in data:
        return pd.DataFrame()
    data["SMA20"] = data["Close"].rolling(20).mean()
    data["SMA50"] = data["Close"].rolling(50).mean()
    data["SMA200"] = data["Close"].rolling(200).mean()
    data["EMA20"] = data["Close"].ewm(span=20, adjust=False).mean()
    data["BB_Middle"] = data["Close"].rolling(20).mean()
    data["BB_Std"] = data["Close"].rolling(20).std()
    data["BB_Upper"] = data["BB_Middle"] + 2 * data["BB_Std"]
    data["BB_Lower"] = data["BB_Middle"] - 2 * data["BB_Std"]
    data["MACD"] = data["Close"].ewm(span=12, adjust=False).mean() - data["Close"].ewm(span=26, adjust=False).mean()
    data["MACD_Signal"] = data["MACD"].ewm(span=9, adjust=False).mean()
    data["MACD_Histogram"] = data["MACD"] - data["MACD_Signal"]
    delta = data["Close"].diff()
    average_gain = delta.clip(lower=0).rolling(14).mean()
    average_loss = -delta.clip(upper=0).rolling(14).mean()
    relative_strength = average_gain / average_loss.replace(0, np.nan)
    data["RSI14"] = 100 - (100 / (1 + relative_strength))
    data["AverageVolume20"] = data["Volume"].rolling(20).mean()
    return data.dropna(subset=["Close"])


@st.cache_data(ttl=900, show_spinner=False)
def get_company_fundamentals(ticker):
    try:
        info = yf.Ticker(ticker).get_info()
    except Exception:
        return {}
    if not isinstance(info, dict):
        return {}
    return {
        "Company": info.get("longName") or info.get("shortName"),
        "Market capitalization": info.get("marketCap"),
        "Trailing P/E": info.get("trailingPE"),
        "Forward P/E": info.get("forwardPE"),
        "EPS (TTM)": info.get("trailingEps"),
        "EPS growth": info.get("earningsGrowth"),
        "Revenue (TTM)": info.get("totalRevenue"),
        "Revenue growth": info.get("revenueGrowth"),
        "Profit margin": info.get("profitMargins"),
        "Debt / equity": info.get("debtToEquity"),
        "Return on equity": info.get("returnOnEquity"),
        "Return on assets": info.get("returnOnAssets"),
        "Dividend yield": info.get("dividendYield"),
        "Analyst target (mean)": info.get("targetMeanPrice"),
        "52-week high": info.get("fiftyTwoWeekHigh"),
        "52-week low": info.get("fiftyTwoWeekLow"),
        "Sector": info.get("sector"),
        "Industry": info.get("industry"),
    }


SCREENER_FILTER_COUNT = 13
SCREENER_CONFIG_KEYS = [
    "screener_universe",
    "screener_min_price",
    "screener_min_avg_volume",
    "screener_min_dollar_volume",
    "screener_rsi_range",
    "screener_min_one_month_return",
    "screener_min_three_month_return",
    "screener_max_volatility",
    "screener_min_relative_volume",
    "screener_max_atr",
    "screener_require_sma20",
    "screener_require_sma50",
    "screener_require_sma200",
    "screener_require_macd",
    "screener_limit_beta",
    "screener_beta_range",
    "screener_sort_by",
    "screener_ascending",
    "screener_sector",
    "screener_industry",
]
for _filter_index in range(SCREENER_FILTER_COUNT):
    SCREENER_CONFIG_KEYS.extend([
        f"screener_filter_{_filter_index}_field",
        f"screener_filter_{_filter_index}_operator",
        f"screener_filter_{_filter_index}_lower",
        f"screener_filter_{_filter_index}_upper",
    ])

SCREENER_CONFIG_DEFAULTS = {
    "screener_universe": "NVDA, AAPL, MSFT, AMZN, GOOGL, META, TSLA, AMD, ORCL, PLTR",
    "screener_min_price": 0.0,
    "screener_min_avg_volume": 0,
    "screener_min_dollar_volume": 0,
    "screener_rsi_range": (0, 100),
    "screener_min_one_month_return": -100.0,
    "screener_min_three_month_return": -100.0,
    "screener_max_volatility": 200.0,
    "screener_min_relative_volume": 0.0,
    "screener_max_atr": 100.0,
    "screener_require_sma20": False,
    "screener_require_sma50": False,
    "screener_require_sma200": False,
    "screener_require_macd": False,
    "screener_limit_beta": False,
    "screener_beta_range": (0.0, 2.0),
    "screener_sort_by": "3M (%)",
    "screener_ascending": False,
    "screener_sector": "",
    "screener_industry": "",
}
for _filter_index in range(SCREENER_FILTER_COUNT):
    SCREENER_CONFIG_DEFAULTS.update({
        f"screener_filter_{_filter_index}_field": "— Off —",
        f"screener_filter_{_filter_index}_operator": "≥",
        f"screener_filter_{_filter_index}_lower": 0.0,
        f"screener_filter_{_filter_index}_upper": 100.0,
    })


@st.cache_data(ttl=300)
def get_portfolio_data(ticker, period="2y"):
    data = yf.download(
        ticker,
        period=period,
        auto_adjust=False,
        progress=False,
        group_by="column",
    )

    if isinstance(data.columns, pd.MultiIndex):
        if "Close" in data.columns.get_level_values(0):
            data.columns = data.columns.get_level_values(0)
        elif "Close" in data.columns.get_level_values(1):
            data.columns = data.columns.get_level_values(1)

    if data.empty or "Close" not in data.columns:
        return pd.DataFrame()

    columns = ["Close"]
    if "Adj Close" in data.columns:
        columns.append("Adj Close")
    return data[columns].dropna(subset=["Close"])


@st.cache_data(ttl=60)
def get_portfolio_intraday_data(tickers):
    if not tickers:
        return pd.DataFrame()

    data = yf.download(
        list(tickers),
        period="5d",
        interval="1m",
        auto_adjust=False,
        progress=False,
        group_by="column",
    )
    if data.empty:
        return pd.DataFrame()

    if isinstance(data.columns, pd.MultiIndex):
        if "Close" in data.columns.get_level_values(0):
            prices = data["Close"]
        elif "Close" in data.columns.get_level_values(1):
            prices = data.xs("Close", axis=1, level=1)
        else:
            return pd.DataFrame()
    elif len(tickers) == 1 and "Close" in data.columns:
        prices = data[["Close"]].rename(columns={"Close": tickers[0]})
    else:
        return pd.DataFrame()

    if isinstance(prices, pd.Series):
        prices = prices.to_frame(name=tickers[0])
    return prices.dropna(how="all")


def discover_stock(query):
    try:
        results = yf.Search(query, max_results=8).quotes or []
        equities = [
            x for x in results
            if x.get("quoteType") in ["EQUITY", "ETF"]
            and x.get("symbol")
        ]

        if not equities:
            return None

        exact = [
            x for x in equities
            if x.get("symbol", "").upper() == query.upper()
        ]

        return exact[0] if exact else equities[0]

    except Exception as error:
        raise RuntimeError(f"Yahoo Finance asset search failed: {error}") from error


def calculate_metrics(data):
    prices = data["Close"].dropna()
    returns = prices.pct_change().dropna()

    if len(prices) < 2:
        return {}

    years = len(returns) / 252
    total_return = (prices.iloc[-1] / prices.iloc[0] - 1) * 100

    cagr = (
        ((prices.iloc[-1] / prices.iloc[0]) ** (1 / years) - 1) * 100
        if years > 0 else 0
    )

    volatility = returns.std() * np.sqrt(252) * 100
    sharpe = (
        returns.mean() / returns.std() * np.sqrt(252)
        if returns.std() else 0
    )
    downside_deviation = np.sqrt(np.square(returns.clip(upper=0)).mean())
    sortino = (
        returns.mean() / downside_deviation * np.sqrt(252)
        if downside_deviation else 0
    )

    drawdown = (
        (prices / prices.cummax() - 1).min() * 100
    )

    one_month_return = (
        (prices.iloc[-1] / prices.iloc[-22] - 1) * 100
        if len(prices) >= 22 else np.nan
    )
    year_prices = prices.tail(252)
    year_high = float(year_prices.max())
    year_low = float(year_prices.min())
    latest = float(prices.iloc[-1])

    return {
        "Latest Price": latest,
        "Daily Change": float(returns.iloc[-1] * 100) if len(returns) else 0,
        "1M Return": float(one_month_return),
        "RSI (14)": float(data["RSI14"].iloc[-1]),
        "52W High": year_high,
        "52W Low": year_low,
        "From 52W High": float((latest / year_high - 1) * 100),
        "Average Volume (20D)": float(data["AverageVolume20"].iloc[-1]),
        "Total Return": float(total_return),
        "CAGR": float(cagr),
        "Volatility": float(volatility),
        "Sharpe": float(sharpe),
        "Sortino": float(sortino),
        "Max Drawdown": float(drawdown)
    }


def price_chart(data, ticker):
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=data.index,
        y=data["BB_Upper"],
        name="Bollinger upper",
        line=dict(color="rgba(8,245,239,.28)", width=1, dash="dot"),
        hovertemplate="%{x|%b %d, %Y}<br>Upper band: $%{y:,.2f}<extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data["BB_Lower"],
        name="Bollinger lower",
        line=dict(color="rgba(8,245,239,.28)", width=1, dash="dot"),
        fill="tonexty",
        fillcolor="rgba(8,245,239,.035)",
        hovertemplate="%{x|%b %d, %Y}<br>Lower band: $%{y:,.2f}<extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data["Close"],
        name="Price",
        line=dict(color="#08f5ef", width=2),
        hovertemplate="%{x|%b %d, %Y}<br>Close: $%{y:,.2f}<extra></extra>"
    ))

    for column, color in [
        ("EMA20", "#f4bb55"),
        ("SMA50", "#58a7ff"),
        ("SMA200", "#ff6489")
    ]:
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data[column],
            name=column,
            line=dict(color=color, width=1.2),
            hovertemplate=f"%{{x|%b %d, %Y}}<br>{column}: $%{{y:,.2f}}<extra></extra>"
        ))

    fig.update_layout(
        title=f"{ticker} // PRICE, TREND & VOLATILITY BANDS",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#04121a",
        height=480,
        hovermode="x unified",
        margin=dict(l=55, r=25, t=70, b=45),
        legend=dict(orientation="h", y=1.12, font=dict(size=10)),
        font=dict(family="IBM Plex Mono, monospace", color="#a6d7dc", size=10),
        xaxis=dict(title="SESSION DATE", showgrid=True, gridcolor="rgba(8,245,239,.09)", tickformat="%b %y"),
        yaxis=dict(title="PRICE (USD)", showgrid=True, gridcolor="rgba(8,245,239,.09)", tickprefix="$", tickformat=",.2f", separatethousands=True)
    )

    return fig


def volume_chart(data, ticker):
    fig = go.Figure(go.Bar(
        x=data.index,
        y=data["Volume"],
        name="Volume",
        marker_color="#0daeb7",
        opacity=0.8
    ))
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data["AverageVolume20"],
        name="20D average",
        line=dict(color="#f4bb55", width=1.5)
    ))
    fig.update_layout(
        title=f"{ticker} // DAILY VOLUME",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#04121a",
        height=300,
        margin=dict(l=60, r=25, t=65, b=45),
        hovermode="x unified",
        font=dict(family="IBM Plex Mono, monospace", color="#a6d7dc", size=10),
        xaxis=dict(title="SESSION DATE", showgrid=True, gridcolor="rgba(8,245,239,.09)", tickformat="%b %y"),
        yaxis=dict(title="SHARES", showgrid=True, gridcolor="rgba(8,245,239,.09)", tickformat=",.3s")
    )
    return fig


def momentum_chart(data, ticker):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data.index, y=data["RSI14"], name="RSI (14)",
        line=dict(color="#08f5ef", width=1.7),
        hovertemplate="%{x|%b %d, %Y}<br>RSI: %{y:.2f}<extra></extra>"
    ))
    fig.add_hline(y=70, line_dash="dot", line_color="#ff6489", annotation_text="70")
    fig.add_hline(y=30, line_dash="dot", line_color="#f4bb55", annotation_text="30")
    fig.add_trace(go.Scatter(
        x=data.index, y=data["MACD"], name="MACD",
        line=dict(color="#58a7ff", width=1.4), yaxis="y2",
        hovertemplate="%{x|%b %d, %Y}<br>MACD: %{y:.4f}<extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=data.index, y=data["MACD_Signal"], name="Signal",
        line=dict(color="#f4bb55", width=1.2, dash="dash"), yaxis="y2",
        hovertemplate="%{x|%b %d, %Y}<br>Signal: %{y:.4f}<extra></extra>"
    ))
    fig.add_trace(go.Bar(
        x=data.index, y=data["MACD_Histogram"], name="MACD histogram",
        marker_color="#12889a", opacity=.55, yaxis="y2",
        hovertemplate="%{x|%b %d, %Y}<br>Histogram: %{y:.4f}<extra></extra>"
    ))
    fig.update_layout(
        title=f"{ticker} // MOMENTUM: RSI & MACD",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#04121a",
        height=370,
        margin=dict(l=60, r=60, t=65, b=45),
        hovermode="x unified",
        font=dict(family="IBM Plex Mono, monospace", color="#a6d7dc", size=10),
        legend=dict(orientation="h", y=1.12, font=dict(size=10)),
        xaxis=dict(title="SESSION DATE", showgrid=True, gridcolor="rgba(8,245,239,.09)", tickformat="%b %y"),
        yaxis=dict(title="RSI (0–100)", range=[0, 100], showgrid=True, gridcolor="rgba(8,245,239,.09)", tickformat=".0f"),
        yaxis2=dict(title="MACD", overlaying="y", side="right", showgrid=False, tickformat=".3f")
    )
    return fig


def screen_ticker(ticker, benchmark_returns=None):
    data = get_stock_data(ticker, "1y")
    if data.empty or len(data) < 22:
        return None

    metrics = calculate_metrics(data)
    latest = data.iloc[-1]
    close = data["Close"]
    true_range = pd.concat(
        [
            data["High"] - data["Low"],
            (data["High"] - data["Close"].shift()).abs(),
            (data["Low"] - data["Close"].shift()).abs()
        ],
        axis=1
    ).max(axis=1)
    average_true_range = true_range.rolling(14).mean().iloc[-1]
    paired_returns = None
    if benchmark_returns is not None:
        paired_returns = pd.concat(
            [data["Returns"].rename("asset"), benchmark_returns.rename("benchmark")],
            axis=1
        ).dropna()
    benchmark_variance = (
        paired_returns["benchmark"].var()
        if paired_returns is not None and len(paired_returns) > 1
        else 0
    )
    beta = (
        float(paired_returns["asset"].cov(paired_returns["benchmark"]) / benchmark_variance)
        if benchmark_variance > 0 else np.nan
    )
    fundamentals = get_company_fundamentals(ticker)
    profile_checked_at = datetime.now().astimezone().isoformat(timespec="seconds")

    def numeric_fundamental(name, scale=1):
        value = fundamentals.get(name)
        try:
            value = float(value) * scale
        except (TypeError, ValueError):
            return np.nan
        return value if np.isfinite(value) else np.nan

    return {
        "Ticker": ticker,
        "Price data as of": pd.Timestamp(data.index[-1]).isoformat(),
        "Profile checked at": profile_checked_at,
        "Price ($)": metrics["Latest Price"],
        "Market Cap ($B)": numeric_fundamental("Market capitalization", 1e-9),
        "P/E": numeric_fundamental("Trailing P/E"),
        "Forward P/E": numeric_fundamental("Forward P/E"),
        "EPS growth (%)": numeric_fundamental("EPS growth", 100),
        "Revenue growth (%)": numeric_fundamental("Revenue growth", 100),
        "Dividend yield (%)": numeric_fundamental("Dividend yield", 100),
        "Debt / equity (%)": numeric_fundamental("Debt / equity"),
        "Profit margin (%)": numeric_fundamental("Profit margin", 100),
        "Return on equity (%)": numeric_fundamental("Return on equity", 100),
        "Return on assets (%)": numeric_fundamental("Return on assets", 100),
        "Sector": fundamentals.get("Sector") or "Unavailable",
        "Industry": fundamentals.get("Industry") or "Unavailable",
        "Day (%)": metrics["Daily Change"],
        "1M (%)": metrics["1M Return"],
        "3M (%)": float((close.iloc[-1] / close.iloc[-64] - 1) * 100) if len(close) >= 64 else np.nan,
        "6M (%)": float((close.iloc[-1] / close.iloc[-127] - 1) * 100) if len(close) >= 127 else np.nan,
        "1Y (%)": metrics["Total Return"],
        "RSI (14)": metrics["RSI (14)"],
        "Volatility (%)": metrics["Volatility"],
        "Avg Volume (20D)": metrics["Average Volume (20D)"],
        "Avg $ Volume (20D)": float((data["Close"] * data["Volume"]).rolling(20).mean().iloc[-1]),
        "Rel. Volume": (
            float(latest["Volume"] / latest["AverageVolume20"])
            if latest["AverageVolume20"] > 0 else np.nan
        ),
        "From 52W High (%)": metrics["From 52W High"],
        "From 52W Low (%)": float((metrics["Latest Price"] / float(close.tail(252).min()) - 1) * 100),
        "ATR (14) (%)": float(average_true_range / metrics["Latest Price"] * 100),
        "Max Drawdown (%)": metrics["Max Drawdown"],
        "Beta vs SPY": beta,
        "Price vs SMA20 (%)": float((latest["Close"] / latest["SMA20"] - 1) * 100),
        "Price vs SMA50 (%)": float((latest["Close"] / latest["SMA50"] - 1) * 100),
        "Price vs SMA200 (%)": float((latest["Close"] / latest["SMA200"] - 1) * 100),
        "MACD Bullish": bool(latest["MACD"] > latest["MACD_Signal"]),
        "Above SMA20": bool(latest["Close"] > latest["SMA20"]),
        "Above SMA50": bool(latest["Close"] > latest["SMA50"]),
        "Above SMA200": bool(latest["Close"] > latest["SMA200"])
    }


@st.cache_data(ttl=900, show_spinner=False)
def get_weather_for_location(location):
    cleaned_location = str(location).strip()
    if not cleaned_location:
        raise ValueError("Enter a location before requesting weather.")
    geocoding_url = (
        "https://geocoding-api.open-meteo.com/v1/search?name="
        f"{quote(cleaned_location)}&count=1&language=en&format=json"
    )
    with urlopen(geocoding_url, timeout=5) as response:
        geocoding = json.loads(response.read().decode("utf-8"))
    places = geocoding.get("results") or []
    if not places:
        raise ValueError(f"No weather location matched “{cleaned_location}”.")
    place = places[0]
    query = (
        "latitude={latitude}&longitude={longitude}"
        "&current=temperature_2m,relative_humidity_2m,apparent_temperature,"
        "precipitation,weather_code,wind_speed_10m"
        "&daily=weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset"
        "&temperature_unit=fahrenheit&wind_speed_unit=mph&precipitation_unit=inch"
        "&timezone=auto&forecast_days=5"
    ).format(latitude=place["latitude"], longitude=place["longitude"])
    with urlopen(f"https://api.open-meteo.com/v1/forecast?{query}", timeout=5) as response:
        weather = json.loads(response.read().decode("utf-8"))
    weather["resolved_location"] = ", ".join(
        part for part in (place.get("name"), place.get("admin1"), place.get("country"))
        if part
    )
    return weather


def describe_weather_code(code):
    descriptions = {
        0: "Clear sky", 1: "Mostly clear", 2: "Partly cloudy",
        3: "Overcast", 45: "Fog", 48: "Rime fog",
        51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
        56: "Freezing drizzle", 57: "Freezing drizzle",
        61: "Light rain", 63: "Rain", 65: "Heavy rain",
        66: "Freezing rain", 67: "Freezing rain",
        71: "Light snow", 73: "Snow", 75: "Heavy snow", 77: "Snow grains",
        80: "Rain showers", 81: "Rain showers", 82: "Heavy showers",
        85: "Snow showers", 86: "Heavy snow showers",
        95: "Thunderstorm", 96: "Thunderstorm / hail", 99: "Thunderstorm / hail"
    }
    return descriptions.get(int(code), "Conditions unavailable")


@st.cache_data(ttl=900, show_spinner=False)
def get_news(feed_url, limit=8):
    request = Request(feed_url, headers={"User-Agent": "NovaMarketIntelligence/1.0"})
    with urlopen(request, timeout=3) as response:
        root = ET.fromstring(response.read())

    stories = []
    for item in root.findall(".//item")[:limit]:
        title = item.findtext("title", default="").strip()
        link = item.findtext("link", default="").strip()
        if title and link.startswith(("https://", "http://")):
            stories.append({
                "Headline": title,
                "Publisher": item.findtext("source", default="News feed").strip(),
                "Published": item.findtext("pubDate", default="").strip(),
                "Link": link
            })
    return stories


def render_news_feed(title, feed_url):
    st.markdown(f'<div class="nova-small">{title}</div>', unsafe_allow_html=True)
    try:
        with st.spinner("CONNECTING TO NEWS FEED..."):
            stories = get_news(feed_url)
    except (OSError, TimeoutError, ValueError, ET.ParseError) as error:
        st.warning(f"{title} is temporarily unavailable ({error}).")
        return []

    if not stories:
        st.info("No headlines are available from this feed right now.")
        return []

    for story in stories:
        title_text = escape(story["Headline"])
        publisher = escape(story["Publisher"])
        published = escape(story["Published"])
        link = escape(story["Link"], quote=True)
        st.markdown(
            f'<a class="nova-headline-card" href="{link}" target="_blank" '
            f'rel="noopener noreferrer">{title_text}'
            f'<span class="nova-headline-meta">{publisher} &nbsp; / &nbsp; '
            f'{published}</span></a>',
            unsafe_allow_html=True
        )
    return stories


def render_market_news():
    market_feed = (
        "https://news.google.com/rss/search?q="
        f"{quote('stock market stocks earnings finance')}"
        "&hl=en-US&gl=US&ceid=US:en"
    )
    local_feed = (
        "https://news.google.com/rss/search?q="
        f"{quote('Naperville OR Chicago Illinois local business news')}"
        "&hl=en-US&gl=US&ceid=US:en"
    )
    market_col, local_col = st.columns(2)
    with market_col:
        market_stories = render_news_feed("MARKET & STOCK NEWS", market_feed)
    with local_col:
        local_stories = render_news_feed("NAPERVILLE / CHICAGO AREA", local_feed)

    stories = market_stories + local_stories
    if stories:
        ticker_text = "   ✦   ".join(
            escape(story["Headline"]) for story in stories
        ) + "   ✦   "
        st.markdown(
            '<div class="nova-headline-rail"><div class="nova-headline-track">'
            f'<span>{ticker_text}</span><span aria-hidden="true">{ticker_text}</span>'
            '</div></div>',
            unsafe_allow_html=True
        )
    return stories


def get_study_ai_settings():
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini").strip()
    try:
        secrets = st.secrets
        api_key = api_key or str(secrets.get("OPENAI_API_KEY", "")).strip()
        model = str(secrets.get("OPENAI_MODEL", model)).strip() or model
    except FileNotFoundError:
        pass
    return api_key, model


def request_study_tutor(
    messages, subject, help_mode, model, api_key, image_data_uri=None
):
    tutor_guidance = (
        "You are NOVA Study Studio, a supportive tutor. Help the student learn "
        "through clear explanations, hints, worked examples on analogous "
        "problems, outlines, feedback, and practice questions. Do not write a "
        "complete graded submission for the student or provide answers to an "
        "active exam. Ask a focused follow-up when the request lacks context. "
        "Be transparent about uncertainty and distinguish facts from guesses."
    )
    request_messages = list(messages)
    if image_data_uri and request_messages:
        last_message = dict(request_messages[-1])
        prompt_text = str(last_message.get("content", ""))
        last_message["content"] = [
            {"type": "text", "text": prompt_text},
            {
                "type": "image_url",
                "image_url": {"url": image_data_uri},
            },
        ]
        request_messages[-1] = last_message
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    f"{tutor_guidance}\nSubject: {subject}. "
                    f"Requested help mode: {help_mode}."
                )
            },
            *request_messages
        ],
        "temperature": 0.4
    }
    request = Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    with urlopen(request, timeout=45) as response:
        result = json.loads(response.read().decode("utf-8"))
    try:
        answer = result["choices"][0]["message"]["content"]
    except (IndexError, KeyError, TypeError) as error:
        raise ValueError("The study assistant returned an invalid response.") from error
    if not isinstance(answer, str):
        raise ValueError("The study assistant returned a non-text response.")
    answer = answer.strip()
    if not answer:
        raise ValueError("The study assistant returned an empty response.")
    return answer


@st.fragment(run_every="60s")
def render_naperville_context():
    weather_col, clock_col = st.columns([1.5, 1])
    with clock_col:
        st.markdown(
            '<div class="nova-small">LIVE LOCAL SYSTEM TIME // YOUR TIMEZONE</div>',
            unsafe_allow_html=True
        )
        components.html(
            """<div style="font:700 2rem Rajdhani,sans-serif;color:#42d7ff;line-height:1.05"
                         id="nova-clock-time"></div>
               <div style="font:600 .68rem 'IBM Plex Mono',monospace;color:#8ea8c2"
                    id="nova-clock-date"></div>
               <script>
                 const timeNode = document.getElementById("nova-clock-time");
                 const dateNode = document.getElementById("nova-clock-date");
                 const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || "local";
                 function updateNovaClock() {
                   const now = new Date();
                   timeNode.textContent = new Intl.DateTimeFormat(undefined, {
                     hour: "2-digit", minute: "2-digit", second: "2-digit",
                     hour12: true
                   }).format(now);
                   dateNode.textContent = new Intl.DateTimeFormat(undefined, {
                     weekday: "long", month: "long", day: "2-digit", year: "numeric"
                   }).format(now) + " / " + timezone;
                 }
                 updateNovaClock();
                 window.setInterval(updateNovaClock, 1000);
               </script>""",
            height=72,
            scrolling=False
        )
    with weather_col:
        location = st.session_state.get("weather_location", "Naperville, Illinois")
        weather = st.session_state.get("weather_data")
        if st.session_state.get("weather_loaded_location") != location:
            weather = None
        st.markdown(
            f'<div class="nova-small">LIVE CONDITIONS // {escape(location.upper())}</div>',
            unsafe_allow_html=True
        )
        button_label = "REFRESH LOCAL WEATHER" if weather else "LOAD LOCAL WEATHER"
        if st.button(button_label, key="load_naperville_weather"):
            try:
                get_weather_for_location.clear()
                with st.spinner("CONNECTING TO WEATHER FEED..."):
                    weather = get_weather_for_location(location)
                st.session_state.weather_data = weather
                st.session_state.weather_loaded_location = location
                st.session_state.weather_error = ""
            except Exception as error:
                st.session_state.weather_error = str(error)
                st.warning(
                    f"Weather is temporarily unavailable ({error}). "
                    "The local clock remains active."
                )
        weather = st.session_state.get("weather_data")
        if st.session_state.get("weather_loaded_location") != location:
            weather = None
        if weather:
            try:
                current = weather["current"]
                st.markdown(
                    f'<span class="nova-weather-temp">{current["temperature_2m"]:.0f}°F</span>'
                    f' &nbsp; {describe_weather_code(current["weather_code"])}',
                    unsafe_allow_html=True
                )
                st.caption(
                    f"Open-Meteo current conditions • feed time {current.get('time', 'unavailable')} "
                    f"{weather.get('timezone', 'local provider timezone')}"
                )
                metrics = st.columns(4)
                metrics[0].markdown(
                    f'<div class="nova-small">FEELS LIKE</div>{current["apparent_temperature"]:.0f}°F',
                    unsafe_allow_html=True
                )
                metrics[1].markdown(
                    f'<div class="nova-small">HUMIDITY</div>{current["relative_humidity_2m"]:.0f}%',
                    unsafe_allow_html=True
                )
                metrics[2].markdown(
                    f'<div class="nova-small">WIND</div>{current["wind_speed_10m"]:.0f} mph',
                    unsafe_allow_html=True
                )
                forecast = weather["daily"]
                forecast_text = "  //  ".join(
                    f'{datetime.fromisoformat(day).strftime("%a")} '
                    f'{forecast["temperature_2m_min"][index]:.0f}°/'
                    f'{forecast["temperature_2m_max"][index]:.0f}° '
                    f'{describe_weather_code(forecast["weather_code"][index])}'
                    for index, day in enumerate(forecast["time"])
                )
                metrics[3].markdown(
                    f'<div class="nova-small">PRECIP.</div>{current["precipitation"]:.2f} in',
                    unsafe_allow_html=True
                )
                st.markdown(
                    f'<div class="nova-small">5-DAY OUTLOOK &nbsp; {forecast_text}</div>',
                    unsafe_allow_html=True
                )
            except (ValueError, KeyError) as error:
                st.warning(
                    f"Weather response was incomplete ({error}). "
                    "The local clock remains active."
                )
        else:
            weather_error = st.session_state.get("weather_error")
            st.caption(
                f"Weather unavailable: {weather_error}"
                if weather_error else
                "Weather loads on request; the local clock is active."
            )


# -----------------------------------------
# PORTFOLIO CONFIGURATION
# -----------------------------------------

if "portfolio" not in st.session_state:
    st.session_state.portfolio = {}

if "radar" not in st.session_state:
    st.session_state.radar = []

persisted_holdings = load_persisted_holdings()
if "weather_location" not in st.session_state:
    st.session_state.weather_location = get_app_setting(
        "weather_location", "Naperville, Illinois"
    )
st.session_state.portfolio = {
    ticker: holding["shares"] for ticker, holding in persisted_holdings.items()
}
st.session_state.radar = get_watchlist()

if "asset_command" not in st.session_state:
    st.session_state.asset_command = ""
if "study_prompt" not in st.session_state:
    st.session_state.study_prompt = ""
if "study_messages" not in st.session_state:
    st.session_state.study_messages = []
if "show_market_news" not in st.session_state:
    st.session_state.show_market_news = False
if "active_page" not in st.session_state:
    st.session_state.active_page = "Command Center"

pages = [
    ("Command Center", "⌂\nCOMMAND"),
    ("Stock Intelligence", "◉\nSTOCKS"),
    ("Market Screener", "▤\nSCREENER"),
    ("Backtesting Lab", "↗\nBACKTEST"),
    ("Galaxy Radar", "◎\nRADAR"),
    ("Portfolio Analytics", "◈\nPORTFOLIO"),
    ("Study Studio", "✎\nSTUDY"),
    ("System Information", "⚙\nSYSTEM")
]
if st.session_state.active_page not in {page_name for page_name, _ in pages}:
    st.session_state.active_page = "Command Center"

st.markdown(
    '<div class="nova-command-header">'
    '<div class="nova-command-brand"><span>✦</span> NOVA '
    '<span>//</span> COMMAND DECK</div>'
    '<div class="nova-spectrum" aria-label="Animated system activity">'
    + "".join("<span></span>" for _ in range(13))
    + '</div></div>',
    unsafe_allow_html=True
)

voice_col, voice_status_col = st.columns([1.1, 2])
with voice_col:
    voice_result = voice_component(
        key="nova_voice_control",
        default={"status": "idle", "transcript": ""},
        response_text=st.session_state.get("last_study_response", "")
    )
with voice_status_col:
    st.markdown(
        '<div class="nova-small">VOICE LINK / CLICK MIC TO SPEAK</div>'
        '<div class="nova-console-note">Say a page name to navigate, or ask '
        'a question while in Study Studio. Browser microphone permission is required.</div>',
        unsafe_allow_html=True
    )
if not isinstance(voice_result, dict):
    voice_result = {"status": "idle", "transcript": ""}
transcript = voice_result.get("transcript", "")
voice_notice = ""
if transcript and transcript != st.session_state.get("last_voice_transcript"):
    st.session_state.last_voice_transcript = transcript
    action, value = parse_voice_command(
        transcript, st.session_state.active_page
    )
    if action == "navigate":
        st.session_state.active_page = value
        voice_notice = f"Voice command opened {value}."
    elif action == "research":
        st.session_state.active_page = "Stock Intelligence"
        st.session_state.stock_search_query = value.upper()
        st.session_state.stock_analysis = None
        st.session_state.voice_research_pending = True
        voice_notice = f"Research request opened for {value.upper()}."
    elif action == "study":
        st.session_state.study_prompt = value
        voice_notice = "Voice question captured for Study Studio."
    else:
        st.session_state.active_page = "Command Center"
        st.session_state.asset_command = value
        voice_notice = f"Voice input captured: “{value}”"

# -----------------------------------------
# CONTROL-DECK NAVIGATION
# -----------------------------------------

if voice_result.get("status") == "error":
    st.warning(
        "Voice recognition could not start. Check microphone permission and "
        f"browser support. ({voice_result.get('message', 'unknown error')})"
    )
elif voice_notice:
    st.caption(voice_notice)

with st.container(key="nova-nav-console"):
    st.markdown(
        '<div class="nova-nav-label">HOLOGRAPHIC SYSTEM CONTROLS / SELECT A MODULE</div>',
        unsafe_allow_html=True
    )
    nav_positions = [[0, 1, 2], [3, None, 4], [5, 6, 7]]
    for row in nav_positions:
        nav_columns = st.columns(3)
        for column, page_index in zip(nav_columns, row):
            if page_index is None:
                column.markdown(
                    '<div class="nova-nav-reactor"><div class="nova-reactor">'
                    '<div class="nova-reactor-label top">NOVA / ONLINE</div>'
                    '<div class="nova-reactor-core">NOVA</div>'
                    '<div class="nova-reactor-label bottom">SYSTEM / READY</div>'
                    '</div></div>',
                    unsafe_allow_html=True
                )
                continue
            destination, label = pages[page_index]
            if column.button(
                label,
                key=f"nav_{destination.lower().replace(' ', '_')}",
                type="primary" if st.session_state.active_page == destination else "secondary",
                use_container_width=False
            ):
                st.session_state.active_page = destination
                st.rerun()

page = st.session_state.active_page

# -----------------------------------------
# COMMAND CENTER
# -----------------------------------------

if page == "Command Center":

    st.markdown('<p class="nova-eyebrow">NOVA // MARKET INTELLIGENCE SYSTEM</p>', unsafe_allow_html=True)
    st.title("NOVA / Command Center")
    st.markdown(
        '<div class="nova-terminal-bar">'
        '<span>TERMINAL / MARKET RESEARCH</span>'
        '<span><strong>LOCAL TIME / BROWSER CLOCK</strong></span>'
        '</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="nova-hud-strip">NOVA ONLINE &nbsp; / &nbsp; '
        'YAHOO FINANCE DATA / ON DEMAND &nbsp; / &nbsp; RESEARCH MODE &nbsp; / &nbsp; '
        'NO TRADE EXECUTION</div>',
        unsafe_allow_html=True
    )
    st.markdown('<div class="nova-panel"><strong>MARKET RESEARCH CONSOLE</strong><br>'
                'Discover an asset, inspect its signals, or scan a custom universe.</div>',
                unsafe_allow_html=True)

    render_naperville_context()

    st.subheader("Market Pulse / Major Indices")
    if st.button("REFRESH MARKET INDEX DATA", key="refresh_market_indices"):
        get_market_indices.clear()
    try:
        market_snapshot = get_market_indices()
    except Exception as error:
        market_snapshot = {}
        st.warning(f"Yahoo Finance index data is unavailable: {error}")
    if market_snapshot:
        index_columns = st.columns(4)
        for column, (label, quote) in zip(index_columns, market_snapshot.items()):
            column.metric(
                label,
                f'{quote["price"]:,.2f}',
                (
                    f'{quote["change_pct"]:+.2f}%'
                    if quote["change_pct"] is not None else None
                ),
            )
        latest_index_time = max(
            quote["as_of"] for quote in market_snapshot.values()
        )
        st.caption(
            f"Yahoo Finance • last daily index data: {latest_index_time} • "
            "values may be delayed and are not an intraday feed."
        )
    else:
        st.info("Market index data has not been returned by the provider.")

    schedule_status, schedule_time = get_us_market_schedule_status()
    st.markdown(
        f'<div class="nova-hud-strip">US EQUITY SCHEDULE / {schedule_status} '
        f'&nbsp; / &nbsp; {schedule_time.strftime("%I:%M %p %Z")}</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Schedule estimate uses weekday US market hours; exchange holidays and special sessions may differ."
    )

    st.markdown("### SYSTEM STATUS")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Research Modules", str(len(pages)))
    col2.metric("Portfolio Assets", len(st.session_state.portfolio))
    col3.metric("Radar Assets", len(st.session_state.radar))
    col4.metric("Market Data Link", "AVAILABLE" if market_snapshot else "UNAVAILABLE")

    portfolio_symbols = ", ".join(
        escape(symbol) for symbol in st.session_state.portfolio
    ) or "No holdings configured"
    radar_symbols = ", ".join(
        escape(symbol) for symbol in st.session_state.radar
    ) or "Radar is waiting for assets"
    left_panel, reactor_panel, right_panel = st.columns([1, 1.2, 1])
    with left_panel:
        st.markdown(
            '<div class="nova-console-panel">'
            '<div class="nova-console-title">Signal channels / 01</div>'
            '<div class="nova-console-row"><span>PRICE HISTORY</span><strong>ON DEMAND</strong></div>'
            '<div class="nova-console-row"><span>MARKET SCREENER</span><strong>READY</strong></div>'
            '<div class="nova-console-row"><span>HEADLINE FEEDS</span><strong>RSS</strong></div>'
            '<div class="nova-console-row"><span>VOICE LINK</span><strong>CLICK TO START</strong></div>'
            '<div class="nova-console-note">Research tools only. Data availability '
            'depends on the external providers.</div>'
            '</div>',
            unsafe_allow_html=True
        )
    with reactor_panel:
        st.markdown(
            '<div class="nova-orbit-wrap"><div class="nova-reactor">'
            '<div class="nova-reactor-label top">NOVA / COMMAND DECK</div>'
            '<div class="nova-reactor-core">NOVA</div>'
            '<div class="nova-reactor-label bottom">MARKET // RESEARCH</div>'
            '</div></div>',
            unsafe_allow_html=True
        )
    with right_panel:
        st.markdown(
            '<div class="nova-console-panel">'
            '<div class="nova-console-title">Active watch / 02</div>'
            f'<div class="nova-console-row"><span>PORTFOLIO</span>'
            f'<strong>{len(st.session_state.portfolio):02d} ASSETS</strong></div>'
            f'<div class="nova-watchlist">{portfolio_symbols}</div>'
            f'<div class="nova-console-row"><span>GALAXY RADAR</span>'
            f'<strong>{len(st.session_state.radar):02d} SIGNALS</strong></div>'
            f'<div class="nova-watchlist">{radar_symbols}</div>'
            '</div>',
            unsafe_allow_html=True
        )

    st.divider()

    st.subheader("Voice / Asset Discovery")
    st.caption(
        "Use the command-deck microphone for ticker lookup or say a page "
        "name such as “market screener” to navigate. Microphone starts only "
        "after your click and requires browser permission."
    )
    if voice_notice:
        st.info(voice_notice)
    command = st.text_input(
        "Enter a company name or ticker",
        placeholder="Example: NVIDIA, AAPL, Microsoft...",
        key="asset_command"
    )

    if st.button("RESOLVE ASSET", use_container_width=True):
        if command:
            try:
                match = discover_stock(command)
            except RuntimeError as error:
                st.error(str(error))
            else:
                if match:
                    st.session_state.selected_ticker = match["symbol"]
                    st.session_state.selected_name = (
                        match.get("longname")
                        or match.get("shortname")
                        or match["symbol"]
                    )
                    st.success(
                        f"Resolved: {st.session_state.selected_name} "
                        f"({match['symbol']})"
                    )
                    st.info("Open Stock Intelligence to inspect the asset.")
                else:
                    st.error("No matching listed stock or ETF was found.")

    st.divider()

    st.subheader("Portfolio Watchlist")

    portfolio_table = pd.DataFrame([
        {"Ticker": ticker, "Shares": shares}
        for ticker, shares in st.session_state.portfolio.items()
    ])

    st.dataframe(portfolio_table, use_container_width=True, hide_index=True)
    if st.button("LOAD HOLDINGS / RADAR MOVERS", key="load_watchlist_movers"):
        mover_rows = []
        for symbol in dict.fromkeys(
            [*st.session_state.portfolio, *st.session_state.radar]
        ):
            try:
                history = get_stock_data(symbol, "5d")
                if len(history) > 1:
                    prior = float(history["Close"].iloc[-2])
                    latest = float(history["Close"].iloc[-1])
                    mover_rows.append({
                        "Ticker": symbol,
                        "Latest Price": latest,
                        "Change (%)": (latest / prior - 1) * 100 if prior else np.nan,
                        "Last Updated": str(history.index[-1]),
                    })
            except Exception:
                continue
        st.session_state.command_movers = mover_rows
    movers = st.session_state.get("command_movers", [])
    if movers:
        st.dataframe(
            pd.DataFrame(movers).sort_values("Change (%)", ascending=False),
            hide_index=True,
            use_container_width=True,
            column_config={
                "Latest Price": st.column_config.NumberColumn(format="$%.2f"),
                "Change (%)": st.column_config.NumberColumn(format="%.2f%%"),
            },
        )
        st.caption("Movers are limited to your saved holdings and radar assets; data source is Yahoo Finance.")
    st.divider()
    st.subheader("Live Intelligence Feeds")
    if st.button(
        "REFRESH LIVE HEADLINES" if st.session_state.show_market_news
        else "LOAD LIVE HEADLINES",
        key="load_market_news"
    ):
        st.session_state.show_market_news = True
        get_news.clear()
    if st.session_state.show_market_news:
        render_market_news()
    else:
        st.caption("Live news feeds load when requested.")
    st.markdown(
        '<div class="nova-small">COMMAND DECK &nbsp; • &nbsp; '
        'STOCK INTELLIGENCE &nbsp; • &nbsp; MARKET SCREENER &nbsp; • &nbsp; '
        'BACKTESTING &nbsp; • &nbsp; GALAXY RADAR &nbsp; • &nbsp; '
        'PORTFOLIO &nbsp; • &nbsp; STUDY STUDIO</div>',
        unsafe_allow_html=True
    )

# -----------------------------------------
# STOCK INTELLIGENCE
# -----------------------------------------

elif page == "Stock Intelligence":

    st.markdown('<p class="nova-eyebrow">NOVA // ASSET ANALYSIS</p>', unsafe_allow_html=True)
    st.title("Stock Intelligence")
    st.caption("PRICE ACTION / TREND / MOMENTUM / RISK")

    if "stock_search_query" not in st.session_state:
        st.session_state.stock_search_query = st.session_state.get(
            "selected_ticker", "NVDA"
        )
    query = st.text_input("Company name or ticker", key="stock_search_query")
    period = st.selectbox(
        "Chart period",
        ["1d", "1w", "1mo", "3mo", "6mo", "1y", "5y"],
        index=5,
        key="stock_chart_period",
    )

    voice_research_pending = bool(
        st.session_state.pop("voice_research_pending", False)
    )
    if st.button("ANALYZE ASSET", use_container_width=True) or voice_research_pending:
        st.session_state.stock_analysis = None
        if not query.strip():
            st.warning("Enter a company name or ticker.")
        else:
            try:
                match = discover_stock(query)
                if match:
                    st.session_state.stock_analysis = {
                        "query": query.strip().casefold(),
                        "ticker": match["symbol"],
                        "name": match.get("longname") or match.get("shortname") or match["symbol"],
                    }
                    st.session_state.selected_ticker = match["symbol"]
                else:
                    st.error("Could not identify that stock. Try its ticker symbol.")
            except Exception as error:
                st.error(f"Asset lookup failed: {error}")

    analysis = st.session_state.get("stock_analysis")
    if analysis and analysis["query"] == query.strip().casefold():
        ticker = analysis["ticker"]
        try:
            data = get_stock_data(ticker, "1y")
            chart_data = get_chart_data(ticker, period)
        except Exception as error:
            data, chart_data = pd.DataFrame(), pd.DataFrame()
            st.error(f"Market data request failed: {error}")

        if data.empty:
            st.error("No usable historical price data was returned by Yahoo Finance.")
        else:
            metrics = calculate_metrics(data)
            st.success(f"{analysis['name']} ({ticker})")
            a, b, c = st.columns(3)
            a.metric("Latest Available Price", f"${metrics['Latest Price']:,.2f}")
            b.metric("1-Year Historical Return", f"{metrics['Total Return']:.2f}%")
            c.metric("Annualized Return (CAGR)", f"{metrics['CAGR']:.2f}%")

            d, e, f = st.columns(3)
            d.metric("Day Change", f"{metrics['Daily Change']:.2f}%")
            e.metric("1-Month Return", f"{metrics['1M Return']:.2f}%")
            f.metric("RSI (14)", f"{metrics['RSI (14)']:.1f}")

            g, h, i = st.columns(3)
            g.metric("Annualized Volatility", f"{metrics['Volatility']:.2f}%")
            h.metric("Sharpe Ratio", f"{metrics['Sharpe']:.2f}")
            i.metric("Sortino Ratio", f"{metrics['Sortino']:.2f}")

            j, k, l = st.columns(3)
            j.metric("Maximum Drawdown", f"{metrics['Max Drawdown']:.2f}%")
            j.caption("Calculated from the last year of available data.")
            k.metric("52-Week Range", f"${metrics['52W Low']:,.2f} – ${metrics['52W High']:,.2f}")
            l.metric("From 52-Week High", f"{metrics['From 52W High']:.2f}%")

            latest = data.iloc[-1]
            indicators = st.columns(4)
            indicators[0].metric("EMA (20)", f"${latest['EMA20']:,.2f}")
            indicators[1].metric("SMA (50)", f"${latest['SMA50']:,.2f}")
            indicators[2].metric("SMA (200)", f"${latest['SMA200']:,.2f}")
            indicators[3].metric("MACD", f"{latest['MACD']:.3f}")

            if not chart_data.empty:
                st.plotly_chart(price_chart(chart_data, ticker), use_container_width=True)
                st.plotly_chart(momentum_chart(chart_data, ticker), use_container_width=True)
                if "Volume" in chart_data:
                    st.plotly_chart(volume_chart(chart_data, ticker), use_container_width=True)
                st.caption(
                    f"Chart period: {period} • Yahoo Finance • latest point "
                    f"{chart_data.index[-1]} (provider timestamps may be delayed)."
                )
            else:
                st.info(f"Yahoo Finance did not return chart data for the selected {period} period.")

            fundamental_col, radar_col = st.columns([1.3, 1])
            with fundamental_col:
                st.subheader("Company Fundamentals")
                if st.button("LOAD AVAILABLE FUNDAMENTALS", key="load_fundamentals"):
                    try:
                        st.session_state.fundamental_data = get_company_fundamentals(ticker)
                        st.session_state.fundamental_ticker = ticker
                        st.session_state.fundamental_loaded_at = datetime.now().astimezone().isoformat(timespec="seconds")
                    except Exception as error:
                        st.session_state.fundamental_data = {}
                        st.warning(f"Fundamentals are unavailable: {error}")
                if st.session_state.get("fundamental_ticker") == ticker:
                    fundamentals = st.session_state.get("fundamental_data", {})
                    fundamental_rows = []
                    for label, value in fundamentals.items():
                        if value is None:
                            display = "Unavailable"
                        elif label in {
                            "EPS growth", "Revenue growth", "Profit margin",
                            "Dividend yield", "Return on equity", "Return on assets",
                        }:
                            display = f"{value * 100:.2f}%" if isinstance(value, (int, float)) else "Unavailable"
                        elif label == "Market capitalization" or label == "Revenue (TTM)":
                            display = f"${value:,.0f}" if isinstance(value, (int, float)) else "Unavailable"
                        elif label in {"Trailing P/E", "Forward P/E", "EPS (TTM)", "Analyst target (mean)", "52-week high", "52-week low", "Debt / equity"}:
                            display = f"{value:,.2f}" if isinstance(value, (int, float)) else "Unavailable"
                        else:
                            display = str(value)
                        fundamental_rows.append({"Metric": label, "Value": display})
                    if fundamental_rows:
                        st.dataframe(pd.DataFrame(fundamental_rows), hide_index=True, use_container_width=True)
                        st.caption(
                            "Source: Yahoo Finance company profile • retrieved "
                            f"{st.session_state.get('fundamental_loaded_at', 'time unavailable')}. "
                            "Unavailable means the provider did not supply the metric."
                        )
                else:
                    st.caption("Company metrics load on request; some may be unavailable from the provider.")
            with radar_col:
                st.subheader("Galaxy Radar")
                if st.button("ADD TO GALAXY RADAR", key="add_analyzed_asset"):
                    add_to_watchlist(ticker)
                    st.session_state.radar = get_watchlist()
                    st.success(f"{ticker} saved to the persistent radar watchlist.")

            st.caption(
                f"Price history source: Yahoo Finance • last daily data point "
                f"{data.index[-1].date()}. Historical measurements are not predictions."
            )

# -----------------------------------------
# MARKET SCREENER
# -----------------------------------------

elif page == "Market Screener":

    st.markdown('<p class="nova-eyebrow">NOVA // MARKET SCAN</p>', unsafe_allow_html=True)
    st.title("Market Screener")
    st.caption(
        "Combine live company fundamentals with historical price, liquidity, "
        "momentum, and risk filters across a custom ticker universe."
    )

    try:
        saved_screens = json.loads(get_app_setting("saved_screens", "{}"))
        if not isinstance(saved_screens, dict):
            raise ValueError("Saved screener configurations must be an object.")
    except (json.JSONDecodeError, TypeError, ValueError) as error:
        saved_screens = {}
        st.error(f"Saved screener configurations could not be loaded: {error}")

    config_notice = st.session_state.pop("screen_config_notice", "")
    if config_notice:
        st.success(config_notice)

    saved_names = sorted(
        name for name, config in saved_screens.items()
        if isinstance(name, str) and isinstance(config, dict)
    )
    config_col, load_col, delete_col = st.columns([3, 1, 1])
    selected_config = config_col.selectbox(
        "Saved screening configurations",
        ["Select a saved configuration", *saved_names],
        key="saved_screen_choice",
    )
    if load_col.button(
        "LOAD",
        key="load_screen_config",
        disabled=selected_config == "Select a saved configuration",
    ):
        for key in SCREENER_CONFIG_KEYS:
            if key in saved_screens[selected_config]:
                st.session_state[key] = saved_screens[selected_config][key]
        st.rerun()
    if delete_col.button(
        "DELETE",
        key="delete_screen_config",
        disabled=selected_config == "Select a saved configuration",
    ):
        del saved_screens[selected_config]
        set_app_setting("saved_screens", json.dumps(saved_screens))
        st.session_state.screen_config_notice = (
            f"Deleted saved configuration: {selected_config}."
        )
        st.rerun()

    for key, default in SCREENER_CONFIG_DEFAULTS.items():
        st.session_state.setdefault(key, default)

    universe = st.text_input(
        "Ticker universe",
        key="screener_universe",
        help="Enter comma-separated stock or ETF tickers. Screening is limited to this list."
    )

    with st.expander("Screening criteria", expanded=True):
        first, second, third = st.columns(3)
        min_price = first.number_input(
            "Minimum price ($)", min_value=0.0, step=5.0,
            key="screener_min_price",
        )
        min_avg_volume = second.number_input(
            "Minimum average daily volume",
            min_value=0,
            step=100_000,
            key="screener_min_avg_volume",
        )
        min_dollar_volume = third.number_input(
            "Minimum average dollar volume ($)",
            min_value=0,
            step=1_000_000,
            key="screener_min_dollar_volume",
        )
        fourth, fifth, sixth = st.columns(3)
        rsi_min, rsi_max = fourth.slider(
            "RSI (14) range",
            min_value=0,
            max_value=100,
            key="screener_rsi_range",
        )
        min_one_month_return = fifth.number_input(
            "Minimum 1-month return (%)",
            step=5.0,
            key="screener_min_one_month_return",
        )
        min_three_month_return = sixth.number_input(
            "Minimum 3-month return (%)",
            step=5.0,
            key="screener_min_three_month_return",
        )
        seventh, eighth, ninth = st.columns(3)
        max_volatility = seventh.number_input(
            "Maximum annualized volatility (%)",
            min_value=0.0,
            step=10.0,
            key="screener_max_volatility",
        )
        min_relative_volume = eighth.number_input(
            "Minimum relative volume",
            min_value=0.0,
            step=0.1,
            key="screener_min_relative_volume",
        )
        max_atr = ninth.number_input(
            "Maximum ATR (14) / price (%)",
            min_value=0.0,
            step=1.0,
            key="screener_max_atr",
        )
        tenth, eleventh, twelfth, thirteenth = st.columns(4)
        require_sma20 = tenth.checkbox(
            "Price above 20-day average", key="screener_require_sma20"
        )
        require_sma50 = eleventh.checkbox(
            "Price above 50-day average", key="screener_require_sma50"
        )
        require_sma200 = twelfth.checkbox(
            "Price above 200-day average", key="screener_require_sma200"
        )
        require_macd = thirteenth.checkbox(
            "MACD bullish", key="screener_require_macd"
        )
        limit_beta = st.checkbox(
            "Limit beta versus SPY", key="screener_limit_beta"
        )
        if limit_beta:
            beta_min, beta_max = st.slider(
                "Beta range",
                min_value=-2.0,
                max_value=4.0,
                step=0.1,
                key="screener_beta_range",
            )
        else:
            beta_min, beta_max = (0.0, 2.0)
        sort_by = st.selectbox(
            "Rank results by",
            ["3M (%)", "1M (%)", "1Y (%)", "RSI (14)", "Rel. Volume",
             "Avg $ Volume (20D)", "Beta vs SPY", "Max Drawdown (%)",
             "Market Cap ($B)", "P/E", "Revenue growth (%)"],
            key="screener_sort_by",
        )
        ascending = st.checkbox(
            "Sort low to high", key="screener_ascending"
        )
        st.markdown("#### Fundamental & additional filters")
        st.caption(
            "Yahoo Finance company-profile data is optional and may be unavailable. "
            "An active filter excludes assets where its value is missing."
        )
        filter_options = [
            "— Off —",
            "Market cap ($B)",
            "Share price ($)",
            "Trailing P/E",
            "Forward P/E",
            "EPS growth (%)",
            "Revenue growth (%)",
            "Dividend yield (%)",
            "Debt / equity (%)",
            "Profit margin (%)",
            "Return on equity (%)",
            "Return on assets (%)",
            "Relative strength / RSI (14)",
            "Average trading volume (20D)",
        ]
        field_columns = {
            "Market cap ($B)": "Market Cap ($B)",
            "Share price ($)": "Price ($)",
            "Trailing P/E": "P/E",
            "Forward P/E": "Forward P/E",
            "EPS growth (%)": "EPS growth (%)",
            "Revenue growth (%)": "Revenue growth (%)",
            "Dividend yield (%)": "Dividend yield (%)",
            "Debt / equity (%)": "Debt / equity (%)",
            "Profit margin (%)": "Profit margin (%)",
            "Return on equity (%)": "Return on equity (%)",
            "Return on assets (%)": "Return on assets (%)",
            "Relative strength / RSI (14)": "RSI (14)",
            "Average trading volume (20D)": "Avg Volume (20D)",
        }
        filter_criteria = []
        for filter_index in range(SCREENER_FILTER_COUNT):
            fields = st.columns([2.2, 1.1, 1, 1])
            field = fields[0].selectbox(
                f"Metric {filter_index + 1}",
                filter_options,
                key=f"screener_filter_{filter_index}_field",
            )
            operator = fields[1].selectbox(
                "Condition",
                ["≥", "≤", "Between"],
                key=f"screener_filter_{filter_index}_operator",
            )
            lower = fields[2].number_input(
                "Threshold",
                key=f"screener_filter_{filter_index}_lower",
            )
            upper = fields[3].number_input(
                "Upper bound",
                key=f"screener_filter_{filter_index}_upper",
            )
            if field != "— Off —":
                filter_criteria.append({
                    "field": field_columns[field],
                    "operator": operator,
                    "lower": lower,
                    "upper": upper,
                })
        sector_filter_col, industry_filter_col = st.columns(2)
        sector_contains = sector_filter_col.text_input(
            "Sector contains",
            key="screener_sector",
            placeholder="Optional",
        )
        industry_contains = industry_filter_col.text_input(
            "Industry contains",
            key="screener_industry",
            placeholder="Optional",
        )

    save_name_col, save_config_col = st.columns([3, 1])
    save_name = save_name_col.text_input(
        "Save current screening configuration as",
        key="screener_save_name",
        placeholder="e.g. Large-cap growth",
    )
    if save_config_col.button("SAVE CONFIGURATION", key="save_screen_config"):
        clean_name = save_name.strip()
        if not clean_name:
            st.error("Enter a name for this screening configuration.")
        else:
            saved_screens[clean_name[:100]] = {
                key: st.session_state.get(key)
                for key in SCREENER_CONFIG_KEYS
                if key in st.session_state
            }
            set_app_setting("saved_screens", json.dumps(saved_screens))
            st.session_state.screen_config_notice = (
                f"Saved screening configuration: {clean_name[:100]}."
            )
            st.rerun()

    if st.button("RUN MARKET SCAN", use_container_width=True):
        tickers = list(dict.fromkeys(
            ticker.strip().upper()
            for ticker in universe.split(",")
            if ticker.strip()
        ))

        if not tickers:
            st.error("Enter at least one ticker to scan.")
        else:
            screen_rows = []
            unavailable = []
            try:
                benchmark_data = get_stock_data("SPY", "1y")
            except Exception as error:
                benchmark_data = pd.DataFrame()
                st.warning(f"SPY benchmark data is unavailable: {error}")
            benchmark_returns = (
                benchmark_data["Returns"] if not benchmark_data.empty else None
            )
            progress = st.progress(0, text="Scanning ticker universe...")

            for index, ticker in enumerate(tickers):
                try:
                    result = screen_ticker(ticker, benchmark_returns)
                    if result is None:
                        unavailable.append(f"{ticker} (no usable history)")
                    else:
                        screen_rows.append(result)
                except Exception as error:
                    unavailable.append(f"{ticker} ({error})")
                progress.progress(
                    (index + 1) / len(tickers),
                    text=f"Scanning {ticker} ({index + 1}/{len(tickers)})"
                )

            progress.empty()

            if screen_rows:
                results = pd.DataFrame(screen_rows)
                filtered = results[
                    (results["Price ($)"] >= min_price)
                    & (results["Avg Volume (20D)"] >= min_avg_volume)
                    & (results["Avg $ Volume (20D)"] >= min_dollar_volume)
                    & results["RSI (14)"].between(rsi_min, rsi_max)
                    & (results["1M (%)"] >= min_one_month_return)
                    & (results["3M (%)"] >= min_three_month_return)
                    & (results["Volatility (%)"] <= max_volatility)
                    & (results["Rel. Volume"] >= min_relative_volume)
                    & (results["ATR (14) (%)"] <= max_atr)
                ]
                try:
                    filtered = apply_screener_filters(
                        filtered,
                        filter_criteria,
                        sector_contains,
                        industry_contains,
                    )
                except ValueError as error:
                    st.error(f"Additional screener filters could not be applied: {error}")
                    filtered = results.iloc[0:0]
                if limit_beta:
                    filtered = filtered[
                        filtered["Beta vs SPY"].between(beta_min, beta_max)
                    ]
                if require_sma20:
                    filtered = filtered[filtered["Above SMA20"]]
                if require_sma50:
                    filtered = filtered[filtered["Above SMA50"]]
                if require_sma200:
                    filtered = filtered[filtered["Above SMA200"]]
                if require_macd:
                    filtered = filtered[filtered["MACD Bullish"]]

                st.markdown(
                    f"**{len(filtered)} of {len(results)} assets match** "
                    f"the active criteria."
                )
                st.dataframe(
                    filtered.sort_values(sort_by, ascending=ascending, na_position="last"),
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Price ($)": st.column_config.NumberColumn(format="$%.2f"),
                        "Market Cap ($B)": st.column_config.NumberColumn(format="$%.2fB"),
                        "P/E": st.column_config.NumberColumn(format="%.2f"),
                        "Forward P/E": st.column_config.NumberColumn(format="%.2f"),
                        "EPS growth (%)": st.column_config.NumberColumn(format="%.2f%%"),
                        "Revenue growth (%)": st.column_config.NumberColumn(format="%.2f%%"),
                        "Dividend yield (%)": st.column_config.NumberColumn(format="%.2f%%"),
                        "Debt / equity (%)": st.column_config.NumberColumn(format="%.2f"),
                        "Profit margin (%)": st.column_config.NumberColumn(format="%.2f%%"),
                        "Return on equity (%)": st.column_config.NumberColumn(format="%.2f%%"),
                        "Return on assets (%)": st.column_config.NumberColumn(format="%.2f%%"),
                        "Day (%)": st.column_config.NumberColumn(format="%.2f%%"),
                        "1M (%)": st.column_config.NumberColumn(format="%.2f%%"),
                        "3M (%)": st.column_config.NumberColumn(format="%.2f%%"),
                        "6M (%)": st.column_config.NumberColumn(format="%.2f%%"),
                        "1Y (%)": st.column_config.NumberColumn(format="%.2f%%"),
                        "RSI (14)": st.column_config.NumberColumn(format="%.1f"),
                        "Volatility (%)": st.column_config.NumberColumn(format="%.2f%%"),
                        "Avg Volume (20D)": st.column_config.NumberColumn(format="%,.0f"),
                        "Avg $ Volume (20D)": st.column_config.NumberColumn(format="$%,.0f"),
                        "Rel. Volume": st.column_config.NumberColumn(format="%.2fx"),
                        "From 52W High (%)": st.column_config.NumberColumn(format="%.2f%%"),
                        "From 52W Low (%)": st.column_config.NumberColumn(format="%.2f%%"),
                        "ATR (14) (%)": st.column_config.NumberColumn(format="%.2f%%"),
                        "Max Drawdown (%)": st.column_config.NumberColumn(format="%.2f%%"),
                        "Beta vs SPY": st.column_config.NumberColumn(format="%.2f"),
                        "Price vs SMA20 (%)": st.column_config.NumberColumn(format="%.2f%%"),
                        "Price vs SMA50 (%)": st.column_config.NumberColumn(format="%.2f%%"),
                        "Price vs SMA200 (%)": st.column_config.NumberColumn(format="%.2f%%")
                    }
                )
                st.caption(
                    "Price history and company profile: Yahoo Finance. Price date and "
                    "profile lookup time are shown per row; company-profile responses "
                    "may be cached for up to 15 minutes. Missing metrics are unavailable."
                )
                if filtered.empty:
                    st.info("No assets match all selected criteria.")
            else:
                st.error("No usable market data was returned for the entered tickers.")

            if unavailable:
                st.warning(f"Skipped tickers with unavailable data: {', '.join(unavailable)}")

    st.caption(
        "Scan universe is user-defined. Metrics use recent historical data; "
        "beta is estimated against SPY and these screens are not investment advice."
    )

# -----------------------------------------
# GALAXY RADAR
# -----------------------------------------

elif page == "Galaxy Radar":

    st.title("Galaxy Intelligence Radar")
    st.caption("DISCOVERED ASSETS / RESEARCH WATCHLIST")

    new_ticker = st.text_input(
        "Add a company or ticker",
        placeholder="Example: AMD"
    )

    if st.button("DISCOVER AND ADD"):
        try:
            match = discover_stock(new_ticker)
            if match:
                ticker = match["symbol"]
                add_to_watchlist(ticker)
                st.session_state.radar = get_watchlist()
                st.success(
                    f"{match.get('longname') or match.get('shortname')} "
                    f"({ticker}) saved to the radar."
                )
            else:
                st.error("No matching stock found.")
        except Exception as error:
            st.error(f"Asset search failed: {error}")

    if st.session_state.radar:
        radar_rows = []
        radar_points = []
        radar_errors = []
        for ticker in st.session_state.radar:
            try:
                data = get_stock_data(ticker, "1y")
                if data.empty:
                    radar_errors.append(f"{ticker}: no current price history")
                    continue
                metrics = calculate_metrics(data)
                radar_rows.append({
                    "Ticker": ticker,
                    "Latest Price": metrics["Latest Price"],
                    "Day Change (%)": metrics["Daily Change"],
                    "1Y Return (%)": metrics["Total Return"],
                    "Volatility (%)": metrics["Volatility"],
                    "Sharpe": metrics["Sharpe"],
                    "Last Updated": str(data.index[-1]),
                })
                daily_angle = np.radians((metrics["Daily Change"] + 10) * 18)
                distance = 18 + min(abs(metrics["Total Return"]), 80) / 100 * 28
                radar_points.append(
                    f'<span class="nova-radar-point" title="{escape(ticker)} / '
                    f'day {metrics["Daily Change"]:+.2f}% / '
                    f'1Y {metrics["Total Return"]:+.2f}%" '
                    f'style="left:{50 + distance * np.sin(daily_angle):.1f}%;'
                    f'top:{50 - distance * np.cos(daily_angle):.1f}%">'
                    f'{escape(ticker)}</span>'
                )
            except Exception as error:
                radar_errors.append(f"{ticker}: {error}")

        if radar_rows:
            st.markdown(
                '<div class="nova-radar-display">'
                '<div class="nova-radar-crosshair"></div>'
                + "".join(radar_points)
                + '</div>',
                unsafe_allow_html=True,
            )
            st.caption(
                "Live radar sweep • marker direction follows the latest daily move; "
                "distance reflects the magnitude of the 1-year return. This is a "
                "visualization of historical prices, not a trading signal."
            )
            st.dataframe(
                pd.DataFrame(radar_rows),
                use_container_width=True,
                hide_index=True
            )
        if radar_errors:
            st.warning("Some radar assets are unavailable: " + "; ".join(radar_errors))
        st.caption("Source: Yahoo Finance • each row includes its latest available history date.")
        remove_choice = st.selectbox(
            "Remove an asset from radar",
            st.session_state.radar,
            key="radar_remove_choice",
        )
        if st.button("REMOVE FROM RADAR"):
            remove_from_watchlist(remove_choice)
            st.session_state.radar = get_watchlist()
            st.rerun()
    else:
        st.info("Your galaxy radar is waiting for its first asset.")

# -----------------------------------------
# PORTFOLIO ANALYTICS
# -----------------------------------------

elif page == "Portfolio Analytics":

    with st.container(key="portfolio-dashboard"):
        st.markdown(
            '<p class="nova-eyebrow">NOVA // PORTFOLIO SYSTEM</p>',
            unsafe_allow_html=True
        )
        st.title("Portfolio Intelligence")
        st.caption("HOLDINGS / ALLOCATION / HISTORICAL RISK & PERFORMANCE")

        st.caption(
            "Enter the shares in your account below. Nova is not connected to a "
            "brokerage and does not import positions or transactions."
        )
        st.subheader("Edit Holdings")
        holdings_now = load_persisted_holdings()
        edit_choice = st.selectbox(
            "Select a holding or add a new one",
            ["Add new holding", *sorted(holdings_now)],
            key="portfolio_edit_choice",
        )
        current_holding = holdings_now.get(edit_choice, {})
        ticker_input = st.text_input(
            "Ticker symbol",
            value="" if edit_choice == "Add new holding" else edit_choice,
            key=f"portfolio_ticker_{edit_choice}",
            disabled=edit_choice != "Add new holding",
        )
        shares_input = st.number_input(
            "Number of shares",
            min_value=0.0,
            value=float(current_holding.get("shares", 0.0)),
            step=0.01,
            format="%.4f",
            key=f"portfolio_shares_{edit_choice}",
        )
        cost_input = st.text_input(
            "Average purchase price per share (optional, USD)",
            value=(
                f'{current_holding["cost_basis"]:.4f}'
                if current_holding.get("cost_basis") is not None else ""
            ),
            key=f"portfolio_cost_{edit_choice}",
            help="Leave blank until you know the cost basis. Nova will not estimate it.",
        )
        save_col, remove_col = st.columns(2)
        if save_col.button("SAVE HOLDING", type="primary", use_container_width=True):
            try:
                ticker = normalize_ticker(ticker_input)
                cost_basis = float(cost_input) if cost_input.strip() else None
                save_holding(ticker, shares_input, cost_basis)
                st.session_state.portfolio_edit_choice = ticker
                st.session_state.pop("sector_exposure", None)
                st.success(f"{ticker} saved to persistent portfolio storage.")
                st.rerun()
            except ValueError as error:
                st.error(str(error))
        if remove_col.button(
            "REMOVE SELECTED",
            use_container_width=True,
            disabled=edit_choice == "Add new holding",
        ):
            remove_holding(edit_choice)
            st.session_state.portfolio_edit_choice = "Add new holding"
            st.session_state.pop("sector_exposure", None)
            st.success(f"{edit_choice} removed from the portfolio.")
            st.rerun()

        price_history = {}
        data_errors = {}
        for ticker in st.session_state.portfolio:
            try:
                data = get_portfolio_data(ticker)
                if data.empty:
                    data_errors[ticker] = "No closing-price history was returned."
                else:
                    price_history[ticker] = data
            except Exception as error:
                data_errors[ticker] = str(error)

        if data_errors:
            unavailable = ", ".join(
                f"{ticker} ({reason})" for ticker, reason in data_errors.items()
            )
            st.warning(
                "Portfolio data is incomplete; unavailable holdings are excluded "
                f"from the estimates: {unavailable}"
            )

        if price_history:
            intraday_errors = []
            try:
                intraday_data = get_portfolio_intraday_data(
                    tuple(price_history)
                )
            except Exception as error:
                intraday_data = pd.DataFrame()
                intraday_errors.append(str(error))

            intraday_history = {
                ticker: intraday_data[[ticker]].rename(columns={ticker: "Close"})
                for ticker in price_history
                if ticker in intraday_data.columns
            }
            fallback_tickers = sorted(set(price_history) - set(intraday_history))
            if intraday_errors:
                st.warning(
                    "Intraday quotes are unavailable; the portfolio uses the "
                    f"latest daily closes instead ({intraday_errors[0]})."
                )
            elif fallback_tickers:
                st.caption(
                    "Using the latest daily close where an intraday quote is "
                    f"unavailable: {', '.join(fallback_tickers)}."
                )

            try:
                analytics = calculate_portfolio_analytics(
                    st.session_state.portfolio,
                    price_history,
                    intraday_history
                )
            except ValueError as error:
                st.warning(f"Portfolio analytics could not be calculated: {error}")
            else:
                frame = analytics.holdings.copy()
                frame["Average Cost / Share"] = frame["Ticker"].map(
                    lambda symbol: (
                        f'${persisted_holdings[symbol]["cost_basis"]:,.2f}'
                        if persisted_holdings.get(symbol, {}).get("cost_basis") is not None
                        else "NOT ENTERED"
                    )
                )
                frame["Total Cost Basis"] = frame.apply(
                    lambda row: (
                        f'${row["Shares"] * persisted_holdings[row["Ticker"]]["cost_basis"]:,.2f}'
                        if persisted_holdings.get(row["Ticker"], {}).get("cost_basis") is not None
                        else "NOT ENTERED"
                    ),
                    axis=1,
                )
                frame["Unrealized Gain/Loss"] = frame.apply(
                    lambda row: (
                        f'${row["Market Value"] - row["Shares"] * persisted_holdings[row["Ticker"]]["cost_basis"]:+,.2f}'
                        if persisted_holdings.get(row["Ticker"], {}).get("cost_basis") is not None
                        else "NOT ENTERED"
                    ),
                    axis=1,
                )
                frame["Unrealized Return (%)"] = frame.apply(
                    lambda row: (
                        f'{(row["Market Value"] / (row["Shares"] * persisted_holdings[row["Ticker"]]["cost_basis"]) - 1) * 100:+.2f}%'
                        if persisted_holdings.get(row["Ticker"], {}).get("cost_basis") is not None
                        else "NOT ENTERED"
                    ),
                    axis=1,
                )
                a, b, c, d = st.columns(4)
                a.metric(
                    (
                        "Partial Portfolio Value"
                        if data_errors else "Estimated Portfolio Value"
                    ),
                    f"${analytics.total_value:,.2f}"
                )
                b.metric(
                    (
                        "Today's P&L"
                        if analytics.as_of.date()
                        == datetime.now(ZoneInfo("America/New_York")).date()
                        else "Last Session P&L"
                    ),
                    (
                        f"${analytics.daily_change_amount:+,.2f}"
                        if analytics.daily_change_amount is not None else "N/A"
                    ),
                    delta=(
                        f"{analytics.daily_change_pct:+.2f}%"
                        if analytics.daily_change_pct is not None else None
                    ),
                )
                c.metric(
                    "1Y Total Return",
                    (
                        f"{analytics.one_year_return_pct:.2f}%"
                        if analytics.one_year_return_pct is not None else "N/A"
                    )
                )
                d.metric(
                    "1Y Volatility",
                    (
                        f"{analytics.annualized_volatility_pct:.2f}%"
                        if analytics.annualized_volatility_pct is not None else "N/A"
                    )
                )
                st.metric(
                    "1Y Maximum Drawdown",
                    (
                        f"{analytics.max_drawdown_pct:.2f}%"
                        if analytics.max_drawdown_pct is not None else "N/A"
                    )
                )
                quote_time = (
                    analytics.as_of.strftime("%b %d, %I:%M %p %Z")
                    if analytics.as_of.tzinfo
                    else analytics.as_of.strftime("%b %d, %Y")
                )
                st.caption(
                    f"Prices through {quote_time}. P&L compares entered shares "
                    "with prior closes, may be delayed, and is withheld when quote "
                    "dates do not align. Refresh to request quotes again (cached "
                    "for 60 seconds)."
                )

                search_holdings = st.text_input(
                    "Search holdings", key="portfolio_search"
                ).strip().upper()
                sort_holdings = st.selectbox(
                    "Sort holdings by",
                    ["Market Value", "Ticker", "Day Change (%)", "Weight (%)"],
                    key="portfolio_sort",
                )
                visible_frame = frame[
                    frame["Ticker"].str.contains(search_holdings, regex=False)
                ] if search_holdings else frame
                st.dataframe(
                    visible_frame.sort_values(
                        sort_holdings,
                        ascending=(sort_holdings == "Ticker"),
                        na_position="last",
                    ),
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Latest Price": st.column_config.NumberColumn(format="$%.2f"),
                        "Day Change ($)": st.column_config.NumberColumn(format="$%.2f"),
                        "Day Change (%)": st.column_config.NumberColumn(format="%.2f%%"),
                        "1Y Total Return (%)": st.column_config.NumberColumn(
                            format="%.2f%%"
                        ),
                        "Market Value": st.column_config.NumberColumn(format="$%.2f"),
                        "Weight (%)": st.column_config.NumberColumn(format="%.2f%%"),
                    }
                )
                basis_complete = not data_errors and all(
                    persisted_holdings.get(symbol, {}).get("cost_basis") is not None
                    for symbol in analytics.holdings["Ticker"]
                )
                if basis_complete:
                    total_basis = sum(
                        persisted_holdings[row["Ticker"]]["cost_basis"] * row["Shares"]
                        for _, row in analytics.holdings.iterrows()
                    )
                    st.metric(
                        "Unrealized Gain/Loss",
                        f"${analytics.total_value - total_basis:+,.2f}",
                    )
                else:
                    st.caption(
                        "Overall unrealized gain/loss is withheld until a purchase "
                        "price is entered for every held asset."
                    )

                colors = [
                    "#62a8ff", "#a886ff", "#4079d8", "#cf8cff",
                    "#81c4ff", "#8057c9", "#b9a2ff", "#526fe0"
                ]
                fig = go.Figure(go.Pie(
                    labels=frame["Ticker"],
                    values=frame["Market Value"],
                    hole=0.62,
                    marker=dict(
                        colors=[colors[index % len(colors)] for index in range(len(frame))],
                        line=dict(color="#090d1b", width=2)
                    ),
                    hovertemplate="%{label}<br>$%{value:,.2f} (%{percent})<extra></extra>"
                ))
                fig.update_layout(
                    title="CURRENT ALLOCATION",
                    template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#c8d8ff", family="IBM Plex Mono, monospace"),
                    title_font=dict(color="#9fc5ff"),
                    legend=dict(font=dict(color="#c8d8ff"))
                )
                st.plotly_chart(fig, use_container_width=True)

                if st.button("LOAD SECTOR EXPOSURE", key="load_sector_exposure"):
                    sector_values = {}
                    sector_unavailable = []
                    values_by_ticker = frame.set_index("Ticker")["Market Value"]
                    with st.spinner("LOADING COMPANY SECTOR DATA..."):
                        for symbol in frame["Ticker"]:
                            fundamentals = get_company_fundamentals(symbol)
                            sector = fundamentals.get("Sector")
                            if not sector:
                                sector_unavailable.append(symbol)
                                continue
                            sector_values[sector] = (
                                sector_values.get(sector, 0.0)
                                + float(values_by_ticker[symbol])
                            )
                    st.session_state.sector_exposure = {
                        "values": sector_values,
                        "unavailable": sector_unavailable,
                    }
                exposure = st.session_state.get("sector_exposure")
                if exposure:
                    if exposure["values"]:
                        sector_frame = pd.DataFrame([
                            {
                                "Sector": sector,
                                "Market Value": value,
                                "Weight (%)": value / analytics.total_value * 100,
                            }
                            for sector, value in exposure["values"].items()
                        ]).sort_values("Market Value", ascending=False)
                        st.dataframe(
                            sector_frame,
                            hide_index=True,
                            use_container_width=True,
                            column_config={
                                "Market Value": st.column_config.NumberColumn(format="$%.2f"),
                                "Weight (%)": st.column_config.NumberColumn(format="%.2f%%"),
                            },
                        )
                    else:
                        st.info("The provider did not return sector data for these holdings.")
                    if exposure["unavailable"]:
                        st.caption(
                            "Sector unavailable for: "
                            + ", ".join(exposure["unavailable"])
                        )

                if len(frame) > 1:
                    st.subheader("Holdings Correlation")
                    st.dataframe(
                        analytics.correlation,
                        use_container_width=True
                    )
        elif not data_errors:
            st.info("Price information is not available for the configured holdings yet.")

        st.caption(
            "One-year estimates apply the entered share counts to adjusted history; "
            "they are not actual account performance and exclude cash flows, fees, "
            "taxes and transaction history."
        )

# -----------------------------------------
# BACKTESTING LAB
# -----------------------------------------

elif page == "Backtesting Lab":

    st.markdown('<p class="nova-eyebrow">NOVA // HISTORICAL SIMULATION</p>', unsafe_allow_html=True)
    st.title("Backtesting Lab")
    st.caption("RULE-BASED RESEARCH / LONG OR CASH / NO LIVE ORDERS")

    with st.container(border=True):
        controls = st.columns([1.2, 1, 1, 1, 1])
        ticker = controls[0].text_input("Ticker", "NVDA", key="backtest_ticker").strip().upper()
        period = controls[1].selectbox(
            "History", ["1y", "2y", "5y", "10y"], index=2, key="backtest_period"
        )
        fast = controls[2].number_input(
            "Fast average", min_value=2, max_value=200, value=20, key="backtest_fast"
        )
        slow = controls[3].number_input(
            "Slow average", min_value=3, max_value=500, value=50, key="backtest_slow"
        )
        capital = controls[4].number_input(
            "Starting capital ($)",
            min_value=100.0,
            value=10_000.0,
            step=1_000.0,
            key="backtest_capital"
        )
        strategy = st.selectbox(
            "Strategy",
            ["SMA crossover", "EMA crossover"],
            key="backtest_strategy",
        )
        compare_strategies = st.checkbox(
            "Compare SMA and EMA",
            value=True,
            key="backtest_compare_strategies",
        )
        default_end = datetime.now().date()
        default_start = (pd.Timestamp(default_end) - pd.DateOffset(years=5)).date()
        date_columns = st.columns(2)
        start_date = date_columns[0].date_input(
            "Start date",
            value=default_start,
            key="backtest_start_date",
        )
        end_date = date_columns[1].date_input(
            "End date",
            value=default_end,
            key="backtest_end_date",
        )
        cost_bps = st.number_input(
            "Estimated cost per position change (basis points)",
            min_value=0.0,
            max_value=500.0,
            value=10.0,
            step=1.0,
            key="backtest_cost_bps"
        )
        run_backtest = st.button(
            "RUN BACKTEST", type="primary", key="run_backtest"
        )

    if run_backtest:
        st.session_state.pop("backtest_result", None)
        if not ticker:
            st.error("Enter a ticker symbol to backtest.")
        elif fast >= slow:
            st.error("Fast average must be shorter than the slow average.")
        elif start_date >= end_date:
            st.error("Start date must be earlier than end date.")
        else:
            try:
                with st.spinner(f"LOADING {ticker} HISTORICAL DATA..."):
                    history = get_stock_data(ticker, period)
                history = history.loc[
                    (history.index.date >= start_date)
                    & (history.index.date <= end_date)
                ]
                if history.empty or len(history) < slow:
                    st.error(
                        f"Not enough historical data in the selected date range "
                        f"to calculate a {slow}-day average for {ticker}."
                    )
                else:
                    engine = VeyroBacktester(
                        initial_capital=capital,
                        transaction_cost=cost_bps / 10_000
                    )
                    primary_method = "EMA" if strategy.startswith("EMA") else "SMA"
                    results = engine.moving_average_strategy(
                        history,
                        fast=int(fast),
                        slow=int(slow),
                        method=primary_method,
                    )
                    metrics = engine.calculate_metrics(results)
                    comparison = {}
                    if compare_strategies:
                        for method in ("SMA", "EMA"):
                            comparison_results = engine.moving_average_strategy(
                                history,
                                fast=int(fast),
                                slow=int(slow),
                                method=method,
                            )
                            comparison[method] = {
                                "results": comparison_results,
                                "metrics": engine.calculate_metrics(comparison_results),
                            }
                    st.session_state.backtest_result = {
                        "ticker": ticker,
                        "period": period,
                        "fast": int(fast),
                        "slow": int(slow),
                        "method": primary_method,
                        "results": results,
                        "metrics": metrics,
                        "comparison": comparison,
                    }
            except Exception as error:
                st.error(f"Backtest could not run: {error}")

    backtest_result = st.session_state.get("backtest_result")
    if backtest_result:
        metrics = backtest_result["metrics"]
        st.markdown(
            f'<div class="nova-hud-strip">RESULTS / {escape(backtest_result["ticker"])}'
            f' / {backtest_result["method"]} {backtest_result["fast"]}:{backtest_result["slow"]}'
            f' / {escape(backtest_result["period"])}</div>',
            unsafe_allow_html=True
        )
        metric_columns = st.columns(4)
        metric_columns[0].metric("Strategy Return", f'{metrics["Total Return (%)"]:.2f}%')
        metric_columns[1].metric("Buy & Hold", f'{metrics["Benchmark Return (%)"]:.2f}%')
        metric_columns[2].metric("Max Drawdown", f'{metrics["Maximum Drawdown (%)"]:.2f}%')
        metric_columns[3].metric("Ending Capital", f'${metrics["Ending Capital ($)"]:,.2f}')
        more_metrics = st.columns(4)
        more_metrics[0].metric("Annualized Return", f'{metrics["Annualized Return (%)"]:.2f}%')
        more_metrics[1].metric("Sharpe Ratio", f'{metrics["Sharpe Ratio"]:.2f}')
        more_metrics[2].metric("Annualized Volatility", f'{metrics["Annualized Volatility (%)"]:.2f}%')
        more_metrics[3].metric("Position Changes", metrics["Position Changes"])

        results = backtest_result["results"]
        equity_chart = go.Figure()
        equity_chart.add_trace(go.Scatter(
            x=results.index,
            y=results["Strategy_Equity"],
            name="Strategy",
            line=dict(color="#08f5ef", width=2)
        ))
        equity_chart.add_trace(go.Scatter(
            x=results.index,
            y=results["Benchmark_Equity"],
            name="Buy & Hold",
            line=dict(color="#f4bb55", width=1.5)
        ))
        for method, result_set in backtest_result["comparison"].items():
            if method == backtest_result["method"]:
                continue
            equity_chart.add_trace(go.Scatter(
                x=result_set["results"].index,
                y=result_set["results"]["Strategy_Equity"],
                name=f"{method} crossover",
                line=dict(color="#a886ff", width=1.5),
            ))
        equity_chart.update_layout(
            title="SIMULATED EQUITY / STRATEGY VS BUY & HOLD",
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#04121a",
            height=440,
            hovermode="x unified",
            margin=dict(l=55, r=25, t=65, b=45),
            font=dict(family="IBM Plex Mono, monospace", color="#a6d7dc", size=10),
            xaxis=dict(title="SESSION DATE", gridcolor="rgba(8,245,239,.09)"),
            yaxis=dict(title="ACCOUNT VALUE (USD)", tickprefix="$", gridcolor="rgba(8,245,239,.09)")
        )
        st.plotly_chart(equity_chart, use_container_width=True)
        drawdown = results["Strategy_Equity"] / results["Strategy_Equity"].cummax() - 1
        drawdown_chart = go.Figure(go.Scatter(
            x=drawdown.index,
            y=drawdown * 100,
            name="Strategy drawdown",
            fill="tozeroy",
            line=dict(color="#ff6489", width=1.5),
        ))
        drawdown_chart.update_layout(
            title="SIMULATED DRAWDOWN",
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#04121a",
            height=280,
            yaxis=dict(title="DRAWDOWN (%)", ticksuffix="%", gridcolor="rgba(8,245,239,.09)"),
            xaxis=dict(title="SESSION DATE", gridcolor="rgba(8,245,239,.09)"),
        )
        st.plotly_chart(drawdown_chart, use_container_width=True)
        if backtest_result["comparison"]:
            comparison_rows = [
                {"Strategy": method, **result_set["metrics"]}
                for method, result_set in backtest_result["comparison"].items()
            ]
            st.dataframe(pd.DataFrame(comparison_rows), hide_index=True, use_container_width=True)
        st.warning(
            "Educational historical simulation only. Signals execute on the "
            "following session to reduce look-ahead bias. Transaction costs are "
            "estimated, dividends and slippage are not modeled, and no orders are placed."
        )
    else:
        st.info("Set the test parameters, then run a backtest to compare the rule with buy-and-hold.")

# -----------------------------------------
# STUDY STUDIO
# -----------------------------------------

elif page == "Study Studio":

    st.markdown('<p class="nova-eyebrow">NOVA // LEARNING SYSTEM</p>', unsafe_allow_html=True)
    st.title("Study / Document Creator")
    st.markdown(
        '<div class="nova-school-note"><strong>YOUR TUTOR, NOT A SUBSTITUTE.</strong> '
        'Use NOVA to understand concepts, plan assignments, practice, draft useful '
        'documents, and get feedback. Review and edit every generated result.</div>',
        unsafe_allow_html=True
    )
    api_key, model = get_study_ai_settings()
    if api_key:
        st.success(f"Study tutor connected / {escape(model)}")
    else:
        st.info(
            "To activate the AI tutor, add OPENAI_API_KEY in Streamlit Cloud "
            "App settings → Secrets. Never put the key in GitHub."
        )
    st.caption(
        "Prompts and attached materials are sent to the configured OpenAI API only "
        "when submitted. Provider usage may incur charges; do not upload sensitive information."
    )

    for message in st.session_state.study_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    saved_documents = get_saved_documents()
    if saved_documents:
        saved_labels = {
            f'{item["title"]} / {item["subject"]} / {item["created_at"]}': item
            for item in saved_documents
        }
        saved_col, load_col = st.columns([4, 1])
        selected_saved = saved_col.selectbox(
            "Saved study work",
            list(saved_labels),
            key="saved_document_choice",
        )
        if load_col.button("LOAD", key="load_saved_document"):
            selected = saved_labels[selected_saved]
            st.session_state.document_title = selected["title"]
            st.session_state.document_subject = selected["subject"]
            st.session_state.document_editor = selected["content"]
            st.rerun()

    if "document_title" not in st.session_state:
        st.session_state.document_title = "NOVA Study Notes"
    if "document_subject" not in st.session_state:
        st.session_state.document_subject = "General"
    if "document_editor" not in st.session_state:
        st.session_state.document_editor = ""

    with st.form("study_question_form", clear_on_submit=False):
        subject_col, mode_col = st.columns(2)
        subject = subject_col.selectbox(
            "Subject",
            ["General", "Math", "Science", "History", "English / Writing", "Computer Science", "Other"],
            key="study_subject"
        )
        help_mode = mode_col.selectbox(
            "How should NOVA help?",
            [
                "Explain a concept",
                "Guide me step by step",
                "Quiz me",
                "Review my draft",
                "Help me plan",
                "Generate a study guide",
                "Summarize notes",
                "Create practice questions",
                "Create an essay or research outline",
                "Create a report or business plan",
                "Create a presentation outline",
                "Create organized class notes",
                "Create flashcards",
            ],
            key="study_help_mode"
        )
        st.text_area(
            "Question, topic, or draft excerpt",
            key="study_prompt",
            height=140,
            placeholder="Ask a question or describe what you are working on..."
        )
        study_upload = st.file_uploader(
            "Attach notes, an assignment, or an image",
            type=["txt", "md", "csv", "docx", "pdf", "png", "jpg", "jpeg", "webp"],
            help="Text is extracted from TXT, Markdown, CSV, DOCX and PDF. Images are sent to vision-capable models.",
        )
        ask_tutor = st.form_submit_button("ASK / GENERATE", type="primary")

    if ask_tutor:
        prompt = st.session_state.study_prompt.strip()
        api_key, model = get_study_ai_settings()
        if not prompt and not study_upload:
            st.warning("Enter a question or attach supported study material.")
        elif not api_key:
            st.error(
                "The study assistant is not connected yet. Add OPENAI_API_KEY "
                "to Streamlit Cloud → App settings → Secrets. The key must not "
                "be committed to GitHub."
            )
        else:
            try:
                extracted_text, image_data_uri = ("", None)
                upload_context = ""
                if study_upload:
                    extracted_text, image_data_uri = read_study_upload(
                        study_upload.name, study_upload.getvalue()
                    )
                    if extracted_text.strip():
                        upload_context = (
                            f"\n\n[Uploaded file: {study_upload.name}]\n"
                            f"{extracted_text}"
                        )
                    elif image_data_uri:
                        prompt = prompt or "Explain the attached assignment and suggest how to approach it."
                full_prompt = prompt + upload_context
                history = [
                    {"role": item["role"], "content": item["content"]}
                    for item in st.session_state.study_messages[-10:]
                ]
                pending_messages = history + [{"role": "user", "content": full_prompt}]
                with st.spinner("NOVA IS THINKING..."):
                    answer = request_study_tutor(
                        pending_messages,
                        subject,
                        help_mode,
                        model,
                        api_key,
                        image_data_uri=image_data_uri,
                    )
                st.session_state.study_messages = pending_messages + [
                    {"role": "assistant", "content": answer}
                ]
                st.session_state.last_study_response = answer
                st.session_state.document_title = (
                    f"{subject} {help_mode}".strip()[:100]
                )
                st.session_state.document_subject = subject
                st.session_state.document_editor = answer
                st.rerun()
            except HTTPError as error:
                st.error(
                    f"The OpenAI API returned HTTP {error.code}. Check the "
                    "configured key, model, and provider account."
                )
            except (URLError, TimeoutError, ValueError, KeyError, OSError) as error:
                st.error(f"Study assistant request failed: {error}")

    st.divider()
    st.subheader("Document workspace")
    st.text_input("Document title", key="document_title")
    st.text_area(
        "Edit before saving or exporting",
        key="document_editor",
        height=360,
        placeholder="Generated or handwritten content appears here. You can edit it before export.",
    )
    save_col, format_col = st.columns([1, 2])
    if save_col.button("SAVE STUDY WORK", type="primary"):
        try:
            save_document(
                st.session_state.document_title,
                st.session_state.document_subject,
                st.session_state.document_editor,
            )
            st.success("Study work saved in Nova's private local database.")
        except ValueError as error:
            st.error(str(error))
    with format_col:
        st.caption("Downloads use your edited text, not an earlier AI response.")
    export_columns = st.columns(4)
    for column, file_type in zip(export_columns, EXPORTS):
        try:
            payload, filename, mime_type = export_document(
                st.session_state.document_title,
                st.session_state.document_editor,
                file_type,
            )
            column.download_button(
                f"DOWNLOAD {file_type.upper()}",
                data=payload,
                file_name=filename,
                mime=mime_type,
                disabled=not st.session_state.document_editor.strip(),
                key=f"download_{file_type.lower().replace(' ', '_')}",
                use_container_width=True,
            )
        except (ImportError, ValueError) as error:
            column.error(f"{file_type} export unavailable: {error}")
# -----------------------------------------
# SYSTEM INFORMATION
# -----------------------------------------

elif page == "System Information":

    st.markdown('<p class="nova-eyebrow">NOVA // CONFIGURATION & HEALTH</p>', unsafe_allow_html=True)
    st.title("System Settings")
    status_left, status_right = st.columns(2)
    status_left.metric(
        "Study AI",
        "CONNECTED" if get_study_ai_settings()[0] else "NOT CONFIGURED",
    )
    status_right.metric(
        "App access password",
        "CONFIGURED" if access_password else "NOT CONFIGURED",
    )
    if not access_password:
        st.warning(
            "This deployment has no NOVA_ACCESS_PASSWORD gate. Restrict access "
            "at the hosting platform before storing private portfolio or study data."
        )

    st.subheader("Weather Location")
    weather_location_input = st.text_input(
        "City, region, or country",
        value=st.session_state.weather_location,
        key="settings_weather_location",
    )
    if st.button("SAVE WEATHER LOCATION", key="save_weather_location"):
        if not weather_location_input.strip():
            st.error("Enter a location.")
        else:
            set_app_setting("weather_location", weather_location_input.strip())
            st.session_state.weather_location = weather_location_input.strip()
            st.session_state.pop("weather_data", None)
            st.session_state.pop("weather_loaded_location", None)
            st.success("Weather location saved. Live conditions load on the command center.")

    st.subheader("Interface")
    reduce_motion_default = get_app_setting("reduce_motion", "0") == "1"
    reduce_motion = st.toggle(
        "Reduce nonessential animations",
        value=reduce_motion_default,
        key="settings_reduce_motion",
    )
    if st.button("SAVE INTERFACE PREFERENCES", key="save_interface_preferences"):
        set_app_setting("reduce_motion", "1" if reduce_motion else "0")
        st.success("Interface preference saved.")
        st.rerun()
    if reduce_motion:
        st.markdown(
            "<style>*,*::before,*::after{animation-duration:.01ms!important;"
            "animation-iteration-count:1!important;transition-duration:.01ms!important}</style>",
            unsafe_allow_html=True,
        )

    st.subheader("Provider & Storage Status")
    st.write(
        "- **Market data:** Yahoo Finance via yfinance; no API key configured; "
        "quotes may be delayed or unavailable.\n"
        "- **Weather:** Open-Meteo geocoding and forecast APIs; no API key required.\n"
        f"- **Study AI:** {escape(get_study_ai_settings()[1])}; "
        f"{'server-side key configured' if get_study_ai_settings()[0] else 'OPENAI_API_KEY required'}.\n"
        "- **Voice:** browser speech recognition; requires supported browser and microphone permission.\n"
        f"- **Private local database:** `{escape(os.environ.get('NOVA_DATA_PATH', '~/.nova/nova.sqlite3'))}` "
        "(contains portfolio, watchlist, settings, and saved study documents)."
    )
    st.caption(
        f"Persistent holdings: {len(load_persisted_holdings())} • "
        f"Radar assets: {len(get_watchlist())} • "
        f"Saved study documents: {len(get_saved_documents())}"
    )
    if st.button("REFRESH MARKET / WEATHER CACHES", key="clear_provider_caches"):
        get_market_indices.clear()
        get_stock_data.clear()
        get_chart_data.clear()
        get_portfolio_data.clear()
        get_portfolio_intraday_data.clear()
        get_weather_for_location.clear()
        st.success("Cached provider responses cleared.")

    st.subheader("Study Session")
    if st.button("CLEAR THIS SESSION'S STUDY CONVERSATION", key="clear_study_history"):
        st.session_state.study_messages = []
        st.session_state.pop("last_study_response", None)
        st.success("This browser session's conversation was cleared.")
        st.rerun()

