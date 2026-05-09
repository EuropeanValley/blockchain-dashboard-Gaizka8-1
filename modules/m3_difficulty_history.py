"""M3 - Difficulty History.

Shows the evolution of Bitcoin's difficulty over the last K adjustment
periods (1 period = 2016 blocks ≈ 2 weeks) and the ratio between the
actual time taken to mine each period and the protocol target
(2016 × 600 s = 1 209 600 s).

The data is built directly from Blockstream by sampling the block at
the start of each adjustment window. This makes the cryptographic
relation explicit: for each period you can see exactly which block
triggered the adjustment.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from api import blockchain_client as bc

EPOCH_LEN = 2016
TARGET_PERIOD_SECONDS = EPOCH_LEN * 600  # 1 209 600


@st.cache_data(ttl=600, show_spinner=False)
def _load_adjustments(n_periods: int) -> pd.DataFrame:
    tip = bc.get_tip_height()
    last_adj = (tip // EPOCH_LEN) * EPOCH_LEN

    rows = []
    for i in range(n_periods):
        h = last_adj - i * EPOCH_LEN
        if h < 0:
            break
        block = bc.get_block_at_height(h)
        rows.append(
            {
                "height": block["height"],
                "timestamp": block["timestamp"],
                "difficulty": block["difficulty"],
                "bits": block["bits"],
            }
        )

    df = pd.DataFrame(rows).sort_values("height").reset_index(drop=True)
    df["date"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
    df["period_seconds"] = df["timestamp"].diff()
    df["ratio_actual_target"] = df["period_seconds"] / TARGET_PERIOD_SECONDS
    df["pct_difficulty_change"] = df["difficulty"].pct_change() * 100
    return df


def _plot_difficulty(df: pd.DataFrame) -> go.Figure:
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
        subplot_titles=(
            "Difficulty across adjustment epochs",
            "Actual / target time per epoch (1.0 = on schedule)",
        ),
    )

    fig.add_trace(
        go.Scatter(
            x=df["date"], y=df["difficulty"],
            mode="lines+markers", name="Difficulty",
            line=dict(width=2),
            hovertemplate="height %{customdata}<br>%{y:.3e}<extra></extra>",
            customdata=df["height"],
        ),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df["date"], y=df["difficulty"],
            mode="markers",
            marker=dict(size=10, symbol="diamond-open"),
            name="Adjustment block", showlegend=False,
        ),
        row=1, col=1,
    )

    fig.add_trace(
        go.Bar(
            x=df["date"][1:], y=df["ratio_actual_target"][1:],
            name="actual / target",
            marker_color=[
                "#06d6a0" if r and r <= 1 else "#e63946"
                for r in df["ratio_actual_target"][1:]
            ],
        ),
        row=2, col=1,
    )
    fig.add_hline(y=1.0, line_dash="dash", line_color="grey", row=2, col=1)

    fig.update_yaxes(type="log", title_text="Difficulty (log)", row=1, col=1)
    fig.update_yaxes(title_text="ratio", row=2, col=1)
    fig.update_layout(height=620, showlegend=False)
    return fig


def render(n_periods: int = 14) -> None:
    st.subheader("M3 · Difficulty History")
    st.caption(
        "Difficulty re-targets every 2016 blocks. We sample the first block "
        "of each epoch and compare the time it actually took to mine the "
        "preceding 2016 blocks against the protocol target of 2 weeks."
    )

    n_periods = st.slider(
        "Adjustment epochs to look back",
        min_value=4, max_value=40, value=n_periods, step=1,
        help="Each epoch = 2016 blocks ≈ 2 weeks."
    )

    try:
        df = _load_adjustments(n_periods)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not build the adjustment history: {exc}")
        return

    if df.empty:
        st.warning("No data available.")
        return

    last = df.iloc[-1]
    c1, c2, c3 = st.columns(3)
    c1.metric(
        "Latest adjustment",
        datetime.fromtimestamp(int(last["timestamp"]), tz=timezone.utc)
            .strftime("%Y-%m-%d"),
    )
    c2.metric("Difficulty now", f"{float(last['difficulty']):.3e}")
    if pd.notna(last["pct_difficulty_change"]):
        c3.metric("Δ vs previous epoch",
                  f"{last['pct_difficulty_change']:+.2f} %")

    st.plotly_chart(_plot_difficulty(df), use_container_width=True)

    st.markdown(
        "**Adjustment formula** (Section 6.1 of the notes): "
        "*new\\_difficulty = old\\_difficulty × (target\\_time / actual\\_time)*, "
        "clamped to a 4× / ¼× range."
    )

    with st.expander("Per-epoch table"):
        view = df.copy()
        view["date"] = view["date"].dt.strftime("%Y-%m-%d")
        view["period_days"] = view["period_seconds"] / 86400
        st.dataframe(
            view[[
                "height", "date", "difficulty",
                "period_days", "ratio_actual_target",
                "pct_difficulty_change",
            ]].rename(columns={
                "ratio_actual_target": "actual/target",
                "pct_difficulty_change": "Δ difficulty (%)",
            }),
            use_container_width=True, hide_index=True,
        )
