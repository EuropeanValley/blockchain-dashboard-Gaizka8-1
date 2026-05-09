"""CryptoChain Analyzer Dashboard — Streamlit entry point.

Run with::

    streamlit run app.py

Each tab is delegated to one of the M1–M4 modules so the file stays
small and the modules can be tested in isolation.
"""

from __future__ import annotations

import streamlit as st

# streamlit-autorefresh is optional: if missing we fall back to a manual
# Refresh button so the dashboard still runs.
try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:  # pragma: no cover
    st_autorefresh = None

from modules.m1_pow_monitor import render as render_m1
from modules.m2_block_header import render as render_m2
from modules.m3_difficulty_history import render as render_m3
from modules.m4_ai_component import render as render_m4


st.set_page_config(
    page_title="CryptoChain Analyzer Dashboard",
    page_icon="⛓️",
    layout="wide",
)

st.title("⛓️ CryptoChain Analyzer Dashboard")
st.markdown(
    "Live cryptographic metrics for the Bitcoin network — "
    "individual project for *Cryptography (UAX, 2025-26)*. "
    "Data source: [Blockstream REST API](https://blockstream.info/api)."
)

with st.sidebar:
    st.header("Settings")
    refresh_interval = st.slider(
        "Auto-refresh every (seconds)",
        min_value=15, max_value=120, value=45, step=5,
    )
    n_blocks_m1 = st.slider("M1 — recent blocks to fetch", 20, 100, 50, step=10)
    n_blocks_m4 = st.slider("M4 — blocks for AI analysis", 50, 500, 200, step=50)
    n_periods_m3 = st.slider("M3 — adjustment epochs", 4, 30, 14, step=1)

    st.markdown("---")
    if st.button("🔄 Force refresh now"):
        st.cache_data.clear()
        st.rerun()

    st.caption("Charts cache results for 60 s to be polite with the public API.")

if st_autorefresh is not None:
    st_autorefresh(interval=refresh_interval * 1000, key="auto_refresh")
else:
    st.warning(
        "`streamlit-autorefresh` is not installed — install it with "
        "`pip install streamlit-autorefresh` or use the sidebar button."
    )

tab1, tab2, tab3, tab4 = st.tabs([
    "M1 · Proof of Work Monitor",
    "M2 · Block Header Analyzer",
    "M3 · Difficulty History",
    "M4 · AI Anomaly Detector",
])

with tab1:
    render_m1(n_blocks=n_blocks_m1)
with tab2:
    render_m2()
with tab3:
    render_m3(n_periods=n_periods_m3)
with tab4:
    render_m4(n_blocks=n_blocks_m4)

st.markdown("---")
st.caption(
    "Built by Gaizka — UAX Cryptography 2025-26. "
    "Repository: github.com/EuropeanValley/blockchain-dashboard-Gaizka8-1"
)
