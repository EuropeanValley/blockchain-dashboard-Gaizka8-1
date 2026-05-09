"""M2 - Block Header Analyzer.

Display the 80-byte block header, parse its six fields, and verify the
Proof of Work locally with ``hashlib`` (the exact derivation explained
in Section 6 of the Blockchain notes).
"""

from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from api import blockchain_client as bc
from modules.crypto_utils import parse_header, target_to_difficulty


@st.cache_data(ttl=60, show_spinner=False)
def _fetch_header(height: int | None = None):
    if height is None:
        height = bc.get_tip_height()
    block_hash = bc.get_block_hash_by_height(height)
    header_hex = bc.get_block_header_hex(block_hash)
    return height, block_hash, header_hex


def _format_bytes_table(header_hex: str) -> str:
    raw = bytes.fromhex(header_hex)
    rows = []
    for i in range(0, len(raw), 16):
        chunk = raw[i : i + 16]
        rows.append(f"`{i:02d}` " + " ".join(f"{b:02x}" for b in chunk))
    return "\n\n".join(rows)


def render() -> None:
    st.subheader("M2 · Block Header Analyzer")
    st.caption(
        "The 80 bytes that miners hash. Verifies SHA256(SHA256(header)) "
        "against the target locally with Python's `hashlib`."
    )

    try:
        tip = bc.get_tip_height()
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not reach the Blockstream API: {exc}")
        return

    target_height = st.number_input(
        "Block height to analyse",
        min_value=0, max_value=tip, value=tip, step=1,
        help="Defaults to the current tip. Pick any historical height.",
    )

    try:
        height, block_hash, header_hex = _fetch_header(int(target_height))
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not fetch block header: {exc}")
        return

    header = parse_header(header_hex)

    st.markdown("**Raw 80-byte header (hex):**")
    st.code(header_hex, language="text")

    with st.expander("Bytes laid out 16 per row"):
        st.markdown(_format_bytes_table(header_hex))

    st.markdown("**Parsed fields** (Bitcoin stores them little-endian; "
                "shown here in display order):")
    ts = datetime.fromtimestamp(header.timestamp, tz=timezone.utc)
    st.table(
        {
            "Field": [
                "version", "prev_block_hash", "merkle_root",
                "timestamp", "bits", "nonce",
            ],
            "Bytes": ["4", "32", "32", "4", "4", "4"],
            "Value": [
                f"{header.version} (0x{header.version:08x})",
                header.prev_hash,
                header.merkle_root,
                f"{header.timestamp}  ({ts.isoformat()})",
                f"0x{header.bits:08x}",
                f"{header.nonce}",
            ],
        }
    )

    st.markdown("### Local Proof of Work verification")
    st.code(
        "import hashlib\n"
        f"raw = bytes.fromhex('{header_hex[:32]}...')   # 80 bytes total\n"
        "h   = hashlib.sha256(hashlib.sha256(raw).digest()).digest()\n"
        "block_hash = h[::-1].hex()   # Bitcoin displays hashes reversed",
        language="python",
    )

    col_a, col_b = st.columns(2)
    col_a.markdown("**Computed (double SHA-256, reversed):**")
    col_a.code(header.hash_hex)
    col_b.markdown("**Reported by the API:**")
    col_b.code(block_hash)

    matches = header.hash_hex == block_hash
    st.success("Hash matches the API ✓") if matches else st.error("Hash mismatch ✗")

    st.markdown("**Target threshold (decoded from `bits`):**")
    st.code(f"{header.target:064x}")
    st.markdown(
        f"Difficulty implied by this target: **{target_to_difficulty(header.target):.6e}**"
    )

    pow_ok = header.pow_valid
    st.markdown(
        f"Hash < Target ?  →  **{'YES — Proof of Work valid ✓' if pow_ok else 'NO — would be rejected ✗'}**"
    )
    st.markdown(
        f"Leading zero **bits** in the hash: **{header.leading_zero_bits}**  \n"
        f"Leading zero **hex digits**: {len(header.hash_hex) - len(header.hash_hex.lstrip('0'))}"
    )
