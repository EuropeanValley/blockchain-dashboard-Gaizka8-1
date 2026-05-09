"""M4 - AI Component: anomaly detector on inter-block times.

Theory baseline
---------------
Bitcoin block production is modelled as a Poisson process with rate
λ = 1 / 600 (one block every ten minutes on average), so the time
between consecutive blocks should follow an **exponential distribution**
with mean 600 s. The cumulative distribution function is

        F(t)  =  1 - exp(-t / mean)

Under the model, the survival probability of seeing an inter-arrival time
greater than ``t`` is ``S(t) = exp(-t / mean)``. This gives us a per-block
p-value that we threshold to flag anomalies.

We compare two detectors:

1. ``StatisticalAnomalyDetector`` — explicit MLE of the exponential
   parameter, p-value < α. Interpretable, no training set required.

2. ``IsolationForestDetector`` — sklearn unsupervised model fitted on a
   small feature window (t, log(t)). Non-parametric baseline.

Evaluation
----------
We do not have labelled mining-pool anomalies, so we evaluate the
detectors with **synthetic anomaly injection**: keep N real inter-block
times, then for K of them inject extreme values. We report Precision,
Recall, F1 and ROC-AUC against the known labels.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from scipy import stats
from sklearn.ensemble import IsolationForest
from sklearn.metrics import (
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from api import blockchain_client as bc

RNG = np.random.default_rng(42)


@dataclass
class StatisticalAnomalyDetector:
    """Two-sided exponential-tail test."""
    alpha: float = 0.01
    mean_: float = 600.0

    def fit(self, dt: np.ndarray) -> "StatisticalAnomalyDetector":
        # MLE for an exponential distribution is the sample mean.
        self.mean_ = float(np.mean(dt))
        return self

    def p_values(self, dt: np.ndarray) -> np.ndarray:
        F = 1 - np.exp(-dt / self.mean_)
        return 2 * np.minimum(F, 1 - F)

    def predict(self, dt: np.ndarray) -> np.ndarray:
        return (self.p_values(dt) < self.alpha).astype(int)

    def scores(self, dt: np.ndarray) -> np.ndarray:
        return -np.log10(np.clip(self.p_values(dt), 1e-12, 1.0))


@dataclass
class IsolationForestDetector:
    contamination: float = 0.05
    model_: IsolationForest | None = None

    def _features(self, dt: np.ndarray) -> np.ndarray:
        return np.column_stack([dt, np.log1p(dt)])

    def fit(self, dt: np.ndarray) -> "IsolationForestDetector":
        self.model_ = IsolationForest(
            contamination=self.contamination, random_state=0,
        ).fit(self._features(dt))
        return self

    def predict(self, dt: np.ndarray) -> np.ndarray:
        assert self.model_ is not None
        return (self.model_.predict(self._features(dt)) == -1).astype(int)

    def scores(self, dt: np.ndarray) -> np.ndarray:
        assert self.model_ is not None
        return -self.model_.score_samples(self._features(dt))


@st.cache_data(ttl=60, show_spinner=False)
def _fetch_dt(n: int) -> tuple[np.ndarray, pd.DataFrame]:
    blocks = bc.get_recent_blocks(n + 1)
    df = pd.DataFrame(blocks)[["height", "id", "timestamp"]]
    df = df.sort_values("height").reset_index(drop=True)
    df["dt_seconds"] = df["timestamp"].diff()
    df = df.dropna().reset_index(drop=True)
    return df["dt_seconds"].to_numpy(), df


def _inject_synthetic_anomalies(dt: np.ndarray, fraction: float = 0.05):
    dt = dt.copy()
    n = len(dt)
    k = max(2, int(n * fraction))
    idx = RNG.choice(n, size=k, replace=False)
    labels = np.zeros(n, dtype=int)
    labels[idx] = 1
    half = k // 2
    mean = float(np.mean(dt))
    dt[idx[:half]] = RNG.uniform(5, 12) * mean
    dt[idx[half:]] = RNG.uniform(0.001, 0.05) * mean
    return dt, labels


def _evaluate(detector, dt: np.ndarray, labels: np.ndarray) -> dict:
    detector.fit(dt)
    preds = detector.predict(dt)
    scores = detector.scores(dt)
    return {
        "precision": precision_score(labels, preds, zero_division=0),
        "recall": recall_score(labels, preds, zero_division=0),
        "f1": f1_score(labels, preds, zero_division=0),
        "roc_auc": roc_auc_score(labels, scores),
    }


def _plot_anomalies(df: pd.DataFrame, anomaly_mask: np.ndarray) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["height"], y=df["dt_seconds"],
            mode="lines+markers", name="Inter-block time",
            line=dict(width=1), marker=dict(size=5),
        )
    )
    if anomaly_mask.any():
        fig.add_trace(
            go.Scatter(
                x=df.loc[anomaly_mask, "height"],
                y=df.loc[anomaly_mask, "dt_seconds"],
                mode="markers",
                marker=dict(size=11, color="#e63946", symbol="x"),
                name="Flagged anomaly",
            )
        )
    fig.add_hline(y=600, line_dash="dot", line_color="grey",
                  annotation_text="Protocol mean (600 s)")
    fig.update_layout(
        title="Inter-block times — flagged anomalies",
        xaxis_title="Block height",
        yaxis_title="Seconds since previous block",
        height=420,
        legend=dict(orientation="h", y=-0.2),
    )
    return fig


def _plot_distribution_fit(dt: np.ndarray, mean: float) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Histogram(
            x=dt, nbinsx=30, histnorm="probability density",
            opacity=0.7, name="Observed",
        )
    )
    xs = np.linspace(0, dt.max() * 1.05, 300)
    fig.add_trace(
        go.Scatter(
            x=xs, y=(1 / mean) * np.exp(-xs / mean),
            mode="lines", name=f"Exponential MLE (mean {mean:.0f} s)",
            line=dict(width=2),
        )
    )
    fig.update_layout(
        title="Empirical distribution vs fitted exponential",
        xaxis_title="Seconds between blocks",
        yaxis_title="Density",
        height=360, bargap=0.02,
        legend=dict(orientation="h", y=-0.2),
    )
    return fig


def render(n_blocks: int = 200) -> None:
    st.subheader("M4 · AI Component — Anomaly Detector")
    st.caption(
        "Two unsupervised detectors over inter-block times, with a "
        "synthetic-injection evaluation."
    )

    n_blocks = st.slider("Blocks to analyse", 50, 500, n_blocks, step=50)
    alpha = st.select_slider(
        "Statistical detector α (significance)",
        options=[0.05, 0.01, 0.005, 0.001], value=0.01,
    )

    try:
        dt_raw, df = _fetch_dt(n_blocks)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not reach the Blockstream API: {exc}")
        return

    mean_obs = float(np.mean(dt_raw))
    ks_stat, ks_p = stats.kstest(dt_raw, "expon", args=(0, mean_obs))

    c1, c2, c3 = st.columns(3)
    c1.metric("Sample size", f"{len(dt_raw)} blocks")
    c2.metric("Empirical mean", f"{mean_obs:.0f} s",
              delta=f"{mean_obs - 600:+.0f} vs 600")
    c3.metric("KS p-value (vs Exp)", f"{ks_p:.3f}",
              help="High p-value = the exponential model is consistent with the data.")

    st.plotly_chart(_plot_distribution_fit(dt_raw, mean_obs),
                    use_container_width=True)

    stat = StatisticalAnomalyDetector(alpha=alpha).fit(dt_raw)
    flags = stat.predict(dt_raw).astype(bool)
    df_flagged = df.assign(anomaly=flags)

    st.markdown("### Live detection")
    st.markdown(
        f"Statistical detector flagged **{flags.sum()}** of {len(dt_raw)} "
        f"recent blocks (α = {alpha})."
    )
    st.plotly_chart(_plot_anomalies(df_flagged, flags),
                    use_container_width=True)

    if flags.any():
        st.markdown("**Flagged blocks:**")
        st.dataframe(
            df_flagged[flags][["height", "id", "dt_seconds"]]
              .rename(columns={"id": "hash", "dt_seconds": "Δt (s)"}),
            use_container_width=True, hide_index=True,
        )
    else:
        st.info("No statistically anomalous gaps in this window — "
                "the chain has been behaving like a textbook Poisson process.")

    st.markdown("### Evaluation (synthetic injection)")
    st.caption(
        "We inject a few extreme inter-block times (very long stalls + "
        "very short bursts) and check whether each detector recovers them."
    )

    dt_eval, labels = _inject_synthetic_anomalies(dt_raw)
    metrics = {
        "Statistical (Exp tail)": _evaluate(
            StatisticalAnomalyDetector(alpha=alpha), dt_eval, labels,
        ),
        "Isolation Forest": _evaluate(
            IsolationForestDetector(contamination=labels.mean()),
            dt_eval, labels,
        ),
    }
    st.dataframe(
        pd.DataFrame(metrics).T.style.format("{:.3f}"),
        use_container_width=True,
    )
    st.caption(
        "Precision/Recall/F1 use the ground-truth labels of the injected "
        "anomalies. ROC-AUC uses each detector's anomaly score."
    )
