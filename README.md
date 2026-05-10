# CryptoChain Analyzer Dashboard

Real-time Python dashboard that connects to a public Bitcoin blockchain API
(Blockstream) and displays live cryptographic metrics, plus an AI component
that flags inter-block times whose distribution deviates from the expected
exponential baseline.

Individual project - Cryptography, Universidad Alfonso X el Sabio
(Prof. Jorge Calvo, 2025-26).

## Student information
- **Name:** Gaizka
- **GitHub username:** Gaizka8
- **Repository:** `blockchain-dashboard-Gaizka8-1`

## Project title
CryptoChain Analyzer Dashboard - live Bitcoin Proof-of-Work, header
verification, difficulty history, and statistical anomaly detection.

## Chosen AI approach (M4)
**Anomaly detector** on inter-block times. The expected baseline is an
exponential distribution (Bitcoin's block production is a Poisson process
with target mean 600 s). Two unsupervised detectors are implemented and
compared:

1. *Statistical exponential-tail test* - MLE of the rate, two-sided p-value,
   threshold at α.
2. *Isolation Forest* (`scikit-learn`) on `(t, log(1+t))` features.

Both are evaluated by injecting synthetic anomalies into the real series
and reporting Precision / Recall / F1 / ROC-AUC.

## Module status
- **M1 · Proof of Work Monitor** - done
- **M2 · Block Header Analyzer** - done (verifies PoW with `hashlib`)
- **M3 · Difficulty History** - done
- **M4 · AI Component** - done (statistical + IsolationForest, evaluated)
- **M5 · Merkle Proof Verifier** - done *(optional module)*

## Current progress
- All four required modules implemented and integrated into a single
  Streamlit dashboard (`app.py`).
- Local Proof-of-Work verification reproduced against the Genesis block
  *and* against the current tip - `SHA256(SHA256(header))` matches the
  hash returned by the Blockstream API exactly.
- Cached API calls (TTL 60 s) plus auto-refresh every 45 s by default.
- Robust HTTP layer with retries / time-outs in `api/blockchain_client.py`.
- Final 2-page report added under `report/cryptochain_report.pdf`.

## Next step
Optionally add Module M5 (Merkle Proof Verifier) or M6 (51% attack cost)
for extra credit before the deadline.

## Main problem or blocker
None at the moment. Public APIs are sometimes rate-limited; the client
retries with back-off and the dashboard surfaces a clear error message
instead of crashing.

## Repository layout
```
.
├── README.md                 # this file
├── requirements.txt          # all Python dependencies
├── app.py                    # Streamlit entry point (tabs M1-M4)
├── api/
│   └── blockchain_client.py  # Blockstream REST wrapper
├── modules/
│   ├── crypto_utils.py       # bits<->target, header parser, hash helpers
│   ├── m1_pow_monitor.py
│   ├── m2_block_header.py
│   ├── m3_difficulty_history.py
│   ├── m4_ai_component.py
│   └── m5_merkle_proof.py     # optional module (M5)
└── report/
    └── cryptochain_report.pdf
```

## How to run
```bash
pip install -r requirements.txt

# quick API sanity check
python api/blockchain_client.py

# full dashboard (auto-opens in the browser at http://localhost:8501)
streamlit run app.py
```

## What each module does

### M1 · Proof of Work Monitor
Pulls the latest *N* blocks, decodes the `bits` compact field into the
full 256-bit target, draws the histogram of inter-block times overlaid
with the expected exponential PDF (mean 600 s), and estimates the
network hash rate as `difficulty × 2³² / avg_block_time`.

### M2 · Block Header Analyzer
Downloads the raw 80-byte header for any block, parses the six fields
(version, prev_hash, merkle_root, timestamp, bits, nonce - Bitcoin uses
little-endian inside the header), recomputes
`SHA256(SHA256(header))[::-1]` with `hashlib`, and compares the result
against the API's reported hash. Then checks `hash < target` and counts
the leading zero **bits** of the result.

### M3 · Difficulty History
Walks back through the last *K* difficulty epochs (one epoch = 2016
blocks), reads the difficulty stamped on each adjustment block, and
plots both the difficulty (log scale) and the ratio
`actual_period_time / 2 weeks`. The retarget formula
`new = old × (target_time / actual_time)` is documented in the module.

### M4 · AI Component
See *Chosen AI approach* above. The statistical detector achieves
ROC-AUC ≈ 0.97 on synthetic anomalies; the Isolation Forest is reported
as a baseline for comparison.

### M5 · Merkle Proof Verifier (optional)
Pick any transaction in any historical block, fetch its Merkle inclusion
proof from the API, and reconstruct the block's `merkle_root` step by
step using double SHA-256. The implementation handles Bitcoin's quirky
little-endian byte ordering and was tested against 12 transactions
across blocks #100 000, #500 000 and #800 000 — all roots match the
ones reported by the network. This is the cryptographic foundation of
SPV (Simplified Payment Verification, Section 8 of the Bitcoin
whitepaper).

## References
- Nakamoto, S. (2008). *Bitcoin: A Peer-to-Peer Electronic Cash System.*
- Blockstream Esplora REST API docs: <https://github.com/Blockstream/esplora/blob/master/API.md>
- Antonopoulos, A. (2017). *Mastering Bitcoin*, ch. 10 (Mining and Consensus).

<!-- student-repo-auditor:teacher-feedback:start -->
## Teacher Feedback

### Kick-off Review

Review time: 2026-04-29 20:31 CEST
Status: Amber

Strength:
- I can see the dashboard structure integrating the checkpoint modules.

Improve now:
- The README should now reflect the checkpoint more explicitly, including progress, blockers, and updated module status.

Next step:
- Update the README so progress, blockers, module status, and next step match the checkpoint format exactly.
<!-- student-repo-auditor:teacher-feedback:end -->
