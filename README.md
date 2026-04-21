# CryptoChain Analyzer Dashboard

Real-time Python dashboard that connects to a public Bitcoin blockchain API and
displays live cryptographic metrics, plus an AI component that adds analytical
value to the raw blockchain data.

Individual project â€” Cryptography, Universidad Alfonso X el Sabio
(Prof. Jorge Calvo, 2025â€“26).

## Student information
- Name: Gaizka
- GitHub username: *(pon aquÃ­ tu nombre de usuario de GitHub)*

## Chosen AI approach (M4)
**Anomaly detector** on inter-block times. The expected baseline is an
exponential distribution (Bitcoin's block production is a Poisson process with
target mean 600 s). Blocks whose inter-arrival time is statistically abnormal
are flagged â€” this may correlate with mining-pool behaviour.
*(Se puede cambiar mÃ¡s adelante si decido otra opciÃ³n.)*

## Module status
- **M1 Â· Proof of Work Monitor** â€” not started
- **M2 Â· Block Header Analyzer** â€” not started
- **M3 Â· Difficulty History** â€” not started
- **M4 Â· AI Component** â€” not started

## Current progress
- Repository accepted from GitHub Classroom.
- README initialised with project info and module status.
- First API call implemented in `api/blockchain_client.py` â€” prints the latest
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
