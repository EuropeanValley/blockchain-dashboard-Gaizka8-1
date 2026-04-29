# CryptoChain Analyzer Dashboard

Real-time Python dashboard that connects to a public Bitcoin blockchain API and
displays live cryptographic metrics, plus an AI component that adds analytical
value to the raw blockchain data.

Individual project - Cryptography, Universidad Alfonso X el Sabio
(Prof. Jorge Calvo, 2025-26).

## Student information
- Name: Gaizka
- GitHub username: Gaizka 8

## Chosen AI approach (M4)
**Anomaly detector** on inter-block times. The expected baseline is an
exponential distribution (Bitcoin's block production is a Poisson process with
target mean 600 s). Blocks whose inter-arrival time is statistically abnormal
are flagged - this may correlate with mining-pool behaviour.

## Module status
- **M1 · Proof of Work Monitor** - not started
- **M2 · Block Header Analyzer** - not started
- **M3 · Difficulty History** - not started
- **M4 · AI Component** - not started

## Current progress
- Repository accepted from GitHub Classroom.
- README initialised with project info and module status.
- First API call implemented in `api/blockchain_client.py` - prints the latest
  block height, hash, difficulty, nonce, bits and transaction count from the
  Blockstream API.

## Next step
Start M1 inside `app.py` using Streamlit: display the current difficulty and
visualise the leading-zero threshold in the 256-bit SHA-256 space.

## Main problem or blocker
None yet.

## How to run
```bash
pip install -r requirements.txt
python api/blockchain_client.py      # quick sanity check
streamlit run app.py                 # full dashboard (coming next)
```

<!-- student-repo-auditor:teacher-feedback:start -->
## Teacher Feedback

### Kick-off Review

Review time: 2026-04-21 09:19 CEST
Status: Amber

Strength:
- Your repository keeps the expected classroom structure.

Improve now:
- The README is present but still misses part of the required kickoff information.

Next step:
- Complete the README fields for student information, AI approach, module status, and next step.
<!-- student-repo-auditor:teacher-feedback:end -->
