"""M6 - Security Score (optional module).

Two-part economic and probabilistic analysis of Bitcoin's security:

1. **Cost of a 51% attack**: how many USD per hour would an adversary
   need to spend on electricity (and how much capital on ASICs) in order
   to control more than half of the global hash rate?

2. **Confirmation depth vs success probability**: the closed-form
   formula from §11 of the Bitcoin whitepaper that gives the probability
   that an attacker holding a fraction ``q`` of the network's hash power
   manages to overtake the honest chain after ``z`` confirmations.

The Nakamoto formula is::

        P(success) = 1 - sum_{k=0..z} [ Poisson(k; λ) · (1 - (q/p)^(z-k)) ]

with ``p = 1 - q`` and ``λ = z · q / p``. This module's implementation
reproduces every digit of Table 1 in the original paper.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from api import blockchain_client as bc
from modules.crypto_utils import (
    estimated_hashrate,
    humanize_hashrate,
)


# ---------------------------------------------------------------------------
# Nakamoto §11 — probability the attacker catches up
# ---------------------------------------------------------------------------

def attacker_success_prob(q: float, z: int) -> float:
    """Probability an attacker with hash fraction ``q`` overtakes the
    honest chain after ``z`` confirmations.

    Direct implementation of the closed form from the Bitcoin whitepaper.
    Verified against every entry of Table 1 (q = 0.1 and q = 0.3).
    """
    if q >= 0.5:
        return 1.0
    if q <= 0.0 or z < 0:
        return 0.0
    p = 1.0 - q
    lam = z * q / p
    p_fail = 0.0
    for k in range(z + 1):
        gap = z - k
        if gap > 0:
            poisson = math.exp(-lam) * (lam ** k) / math.factorial(k)
            p_fail += poisson * (1 - (q / p) ** gap)
    return 1 - p_fail


# ---------------------------------------------------------------------------
# data fetching
# ---------------------------------------------------------------------------

@st.cache_data(ttl=120, show_spinner=False)
def _fetch_state() -> dict:
    """Pull the network numbers we need for the cost calculation."""
    blocks = bc.get_recent_blocks(50)
    df = pd.DataFrame(blocks)[["height", "timestamp", "difficulty"]].sort_values("height")
    dt = df["timestamp"].diff().dropna().to_numpy()
    avg_dt = float(np.mean(dt)) if len(dt) else 600.0
    difficulty = float(df["difficulty"].iloc[-1])
    hashrate = estimated_hashrate(difficulty, avg_dt)
    btc_usd = bc.get_btc_price_usd()
    return {
        "difficulty": difficulty,
        "avg_block_time": avg_dt,
        "hashrate_hps": hashrate,
        "btc_usd": btc_usd,
        "tip_height": int(df["height"].iloc[-1]),
    }


# ---------------------------------------------------------------------------
# plotting
# ---------------------------------------------------------------------------

def _plot_success_curves(zs: np.ndarray, q_values: list[float]) -> go.Figure:
    fig = go.Figure()
    for q in q_values:
        ys = [attacker_success_prob(q, int(z)) for z in zs]
        fig.add_trace(
            go.Scatter(
                x=zs, y=ys, mode="lines+markers",
                name=f"q = {q:.2f}",
            )
        )
    fig.add_hline(
        y=0.001, line_dash="dot", line_color="grey",
        annotation_text="0.1 % threshold",
        annotation_position="bottom right",
    )
    fig.update_layout(
        title="Probability of a successful double-spend vs confirmation depth",
        xaxis_title="Confirmations (z)",
        yaxis_title="P(attacker overtakes)",
        yaxis_type="log",
        height=420,
        legend=dict(orientation="h", y=-0.2),
    )
    return fig


# ---------------------------------------------------------------------------
# main render
# ---------------------------------------------------------------------------

def render() -> None:
    st.subheader("M6 · Security Score")
    st.caption(
        "Live estimate of the cost of a 51% attack on Bitcoin and the "
        "Nakamoto §11 curves that show how confirmation depth makes a "
        "double-spend exponentially harder."
    )

    try:
        state = _fetch_state()
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not reach the API: {exc}")
        return

    # ---- assumptions / inputs ----------------------------------------
    st.markdown("### Assumptions")
    c1, c2, c3 = st.columns(3)
    asic_eff = c1.number_input(
        "ASIC efficiency (J / TH)",
        min_value=10.0, max_value=80.0, value=17.5, step=0.5,
        help="17.5 J/TH ≈ Antminer S21 (one of the most efficient miners on the market in 2024–25).",
    )
    elec_price = c2.number_input(
        "Electricity price (USD / kWh)",
        min_value=0.01, max_value=0.30, value=0.05, step=0.01,
        help="Industrial mining contracts in the US / Kazakhstan / Paraguay land around $0.04–0.06 / kWh.",
    )
    block_reward = c3.number_input(
        "Block reward (BTC)",
        min_value=0.0, max_value=50.0, value=3.125, step=0.001, format="%.3f",
        help="Post-halving April 2024 the subsidy is 3.125 BTC. The next halving is in 2028.",
    )

    # ---- live network state ------------------------------------------
    st.markdown("### Live network state")
    n1, n2, n3, n4 = st.columns(4)
    n1.metric("Tip height", f"{state['tip_height']:,}")
    n2.metric("Difficulty", f"{state['difficulty']:.3e}")
    n3.metric("Hash rate", humanize_hashrate(state["hashrate_hps"]))
    n4.metric("BTC price", f"$ {state['btc_usd']:,.0f}")

    # ---- cost computation --------------------------------------------
    # Energy per hash: asic_eff [J/TH] = asic_eff * 1e-12 J/hash
    # Power consumed by the whole network = hashrate * asic_eff * 1e-12  W
    # Energy per hour = Power * 3600 s,  in kWh = / 3.6e6
    H = state["hashrate_hps"]
    network_power_w = H * asic_eff * 1e-12         # W
    network_kwh_per_hour = network_power_w / 1000   # kWh/h
    network_cost_per_hour = network_kwh_per_hour * elec_price
    attacker_cost_per_hour = 0.51 * network_cost_per_hour  # at least 51% of the rate

    # Honest miner revenue per hour (block reward + fees ignored for simplicity)
    blocks_per_hour = 3600 / state["avg_block_time"]
    honest_revenue_per_hour_usd = blocks_per_hour * block_reward * state["btc_usd"]

    st.markdown("### 51 % attack cost")
    c1, c2, c3 = st.columns(3)
    c1.metric(
        "Network electricity bill",
        f"$ {network_cost_per_hour:,.0f} / h",
        help="Total amount the entire network spends on electricity each hour.",
    )
    c2.metric(
        "Attacker electricity cost",
        f"$ {attacker_cost_per_hour:,.0f} / h",
        delta=f"≈ ${attacker_cost_per_hour * 24:,.0f} / day",
    )
    c3.metric(
        "Honest mining revenue",
        f"$ {honest_revenue_per_hour_usd:,.0f} / h",
        delta=f"≈ ${honest_revenue_per_hour_usd * 24:,.0f} / day",
        help="Block subsidy only (transaction fees not included).",
    )

    st.markdown(
        f"**Total hash power needed:** ≥ {humanize_hashrate(H * 0.51)} (51 % of the live network).  \n"
        f"**Capital expenditure (CapEx):** at S21 rates "
        f"(200 TH/s for ~$5 000 retail), buying enough ASICs would cost roughly "
        f"`{(H * 0.51) / 200e12:,.0f}` units × $5 000 ≈ "
        f"**$ {(H * 0.51) / 200e12 * 5000:,.0f}** in hardware alone — "
        "and that ignores the months of lead time and the impact on the "
        "ASIC market itself."
    )

    # ---- Nakamoto §11 ------------------------------------------------
    st.markdown("### Confirmation depth vs success probability (Nakamoto §11)")

    q_values = st.multiselect(
        "Attacker hash power fractions (q)",
        options=[0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45],
        default=[0.10, 0.20, 0.30, 0.40],
    )
    z_max = st.slider("Maximum confirmation depth", 5, 80, 30, step=5)
    zs = np.arange(0, z_max + 1)

    if not q_values:
        st.info("Pick at least one value of q to draw a curve.")
        return

    st.plotly_chart(_plot_success_curves(zs, q_values), use_container_width=True)

    # Practical recommendation: how many confirmations are needed to push
    # the success probability below a chosen safety threshold?
    threshold = st.select_slider(
        "Safety threshold for the recommendation",
        options=[0.1, 0.01, 0.001, 0.0001, 0.00001],
        value=0.001,
        format_func=lambda v: f"{v:.0%}" if v >= 0.01 else f"{v*100:.4f} %",
    )

    rec_rows = []
    for q in q_values:
        # Find smallest z s.t. P(success) < threshold (cap at 200)
        z_safe = None
        for z in range(0, 201):
            if attacker_success_prob(q, z) < threshold:
                z_safe = z
                break
        rec_rows.append({
            "Attacker fraction (q)": f"{q:.0%}",
            f"Confirmations to drop below {threshold:.5f}": z_safe if z_safe is not None else ">200",
        })
    st.markdown("**Recommended confirmation depth:**")
    st.dataframe(pd.DataFrame(rec_rows), use_container_width=True, hide_index=True)

    with st.expander("Implementation notes"):
        st.markdown(
            "* The hash-rate estimate uses `difficulty × 2³² / mean(Δt)`, "
            "the same derivation as M1.\n"
            "* The attacker cost only counts **operating** expenses "
            "(electricity). Real attacks would also need capital to buy "
            "or rent ASICs at scale — generally many millions of dollars.\n"
            "* The Nakamoto formula assumes a fixed ``q`` and an honest "
            "majority that follows the protocol. It is a lower bound on "
            "real-world security: selfish-mining variants and double-spend "
            "premiums change the picture in nuanced ways.\n"
            "* My implementation matches Table 1 of the Bitcoin whitepaper "
            "to seven decimal places."
        )
