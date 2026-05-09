"""M1 - Proof of Work Monitor.

Live view of the current state of Bitcoin mining:

* Current difficulty and the *target* threshold it represents
  in the 256-bit SHA-256 space (visualised as leading zeros).
* Histogram of the time between the last N blocks, with the theoretical
  exponential PDF (mean = 600 s) overlaid for comparison.
* Estimated network hash rate.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from api import blockchain_client as bc
from modules.crypto_utils import (
    bits_to_target,
    estimated_hashrate,
    humanize_hashrate,
    leading_zero_bits,
)


@st.cache_data(ttl=60, show_spinner=False)
def _fetch_recent(n: int) -> pd.DataFrame:
    blocks = bc.get_recent_blocks(n)
    df = pd.DataFrame(blocks)[
        ["height", "id", "timestamp", "difficulty", "nonce", "bits", "tx_count"]
    ]
    df = df.sort_values("height").reset_index(drop=True)
    df["dt_seconds"] = df["timestamp"].diff()
    return df


def _plot_inter_block_times(dt: np.ndarray) -> go.Figure:
    mean = float(np.mean(dt))
    fig = go.Figure()
    fig.add_trace(
        go.Histogram(
            x=dt, nbinsx=30, histnorm="probability density",
            name="Observed", opacity=0.75,
        )
    )
    xs = np.linspace(0, max(dt) * 1.05, 200)
    fig.add_trace(
        go.Scatter(
            x=xs, y=(1 / 600) * np.exp(-xs / 600),
            mode="lines", name="Expected (Exp, mean 600 s)",
            line=dict(width=2),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=xs, y=(1 / mean) * np.exp(-xs / mean),
            mode="lines", name=f"Empirical (Exp, mean {mean:.0f} s)",
            line=dict(width=2, dash="dash"),
        )
    )
    fig.update_layout(
        title="Inter-block time distribution",
        xaxis_title="Seconds between blocks",
        yaxis_title="Density",
        bargap=0.02,
        legend=dict(orientation="h", y=-0.2),
        height=380,
    )
    return fig


def _plot_target_threshold(target: int, hash_int: int) -> go.Figure:
    """Logarithmic visualisation of the target inside 2**256."""
    log_total = 256
    log_target = math.log2(target) if target > 0 else 0
    log_hash = math.log2(hash_int) if hash_int > 0 else 0

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=["2^256 hash space"], y=[log_total],
            marker_color="#444", name="Total space (2^256)",
            text=["256 bits"], textposition="inside",
        )
    )
    fig.add_hline(
        y=log_target, line_dash="dash", line_color="#e63946",
        annotation_text=f"Target ≈ 2^{log_target:.1f}",
        annotation_position="top right",
    )
    fig.add_hline(
        y=log_hash, line_dash="dot", line_color="#06d6a0",
        annotation_text=f"Latest hash ≈ 2^{log_hash:.1f}",
        annotation_position="bottom right",
    )
    fig.update_layout(
        title="Target threshold inside the 256-bit hash space (log scale)",
        yaxis_title="log2(value)",
        showlegend=False,
        height=420,
    )
    return fig


def render(n_blocks: int = 50) -> None:
    st.subheader("M1 · Proof of Work Monitor")
    st.caption(
        "Live mining state — current difficulty, leading-zero threshold, "
        "inter-block time distribution and estimated network hash rate."
    )

    try:
        df = _fetch_recent(n_blocks)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not reach the Blockstream API: {exc}")
        return

    latest = df.iloc[-1]
    target = bits_to_target(int(latest["bits"]))
    hash_int = int(latest["id"], 16)
    lz_bits = leading_zero_bits(latest["id"])

    dt = df["dt_seconds"].dropna().to_numpy()
    avg_dt = float(np.mean(dt)) if dt.size else 600.0
    hashrate = estimated_hashrate(float(latest["difficulty"]), avg_dt)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tip height", f"{int(latest['height']):,}")
    c2.metric("Difficulty", f"{float(latest['difficulty']):.3e}")
    c3.metric("Avg block time", f"{avg_dt:.0f} s",
              delta=f"{avg_dt - 600:.0f} s vs target")
    c4.metric("Est. hash rate", humanize_hashrate(hashrate))

    st.markdown(
        f"**Latest block hash:** `{latest['id']}`  \n"
        f"**Leading zero bits:** {lz_bits} "
        f"(equivalent to ~{lz_bits / 4:.1f} hex zeros)"
    )

    st.plotly_chart(_plot_target_threshold(target, hash_int),
                    use_container_width=True)

    if dt.size >= 5:
        st.plotly_chart(_plot_inter_block_times(dt), use_container_width=True)
        st.caption(
            "Bitcoin block production is a Poisson process, so inter-block "
            "times should follow an **exponential distribution** with mean "
            "≈ 600 s. Deviations are exploited in M4."
        )
    else:
        st.info("Need a few more blocks to draw the histogram.")

    with st.expander("Recent blocks (raw data)"):
        st.dataframe(df[::-1], use_container_width=True, hide_index=True)
