"""M5 - Merkle Proof Verifier (optional module).

Pick any transaction inside any Bitcoin block and reconstruct, step by
step, its Merkle inclusion proof until we reach the block's Merkle root.

Why this is interesting (Section 7 of the notes): the Merkle root is
one of the six fields hashed by the Proof of Work, so verifying that a
transaction is part of the tree *also* implies it is committed to by the
mined block — without having to download the whole block. This is the
foundation of SPV (Simplified Payment Verification) wallets.
"""

from __future__ import annotations

import streamlit as st

from api import blockchain_client as bc
from modules.crypto_utils import verify_merkle_proof


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_block_and_txids(height: int):
    block_hash = bc.get_block_hash_by_height(height)
    block = bc.get_block(block_hash)
    txids = bc.get_block_txids(block_hash)
    return block_hash, block, txids


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_proof(txid: str) -> dict:
    return bc.get_merkle_proof(txid)


def render() -> None:
    st.subheader("M5 · Merkle Proof Verifier")
    st.caption(
        "Pick any transaction in any block, fetch its Merkle inclusion "
        "proof from the API, and reconstruct the root step by step with "
        "double SHA-256."
    )

    try:
        tip = bc.get_tip_height()
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not reach the Blockstream API: {exc}")
        return

    height = st.number_input(
        "Block height",
        min_value=1, max_value=tip, value=min(800000, tip), step=1,
        help="Defaults to a busy historical block (>3000 tx).",
    )

    try:
        block_hash, block, txids = _fetch_block_and_txids(int(height))
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not fetch block #{height}: {exc}")
        return

    st.markdown(
        f"**Block #{block['height']}** — `{block_hash[:24]}…`  \n"
        f"Transactions in the block: **{len(txids):,}**  \n"
        f"Merkle root reported by the API: `{block['merkle_root']}`"
    )

    if len(txids) == 1:
        st.info(
            "This block contains only the coinbase transaction, so the "
            "Merkle root equals the txid itself (no proof needed)."
        )
        st.code(f"merkle_root == txid == {txids[0]}")
        return

    # Pick a transaction. Default to a non-coinbase tx so the proof is
    # non-trivial.
    options = {f"#{i:>4}  {txid[:18]}…": (i, txid) for i, txid in enumerate(txids)}
    label = st.selectbox(
        "Transaction to verify",
        options.keys(),
        index=min(1, len(options) - 1),  # default to tx[1]
    )
    idx, txid = options[label]

    try:
        proof = _fetch_proof(txid)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not fetch the Merkle proof: {exc}")
        return

    siblings = proof["merkle"]
    pos = proof["pos"]

    computed_root, steps = verify_merkle_proof(txid, siblings, pos)
    matches = computed_root == block["merkle_root"]

    c1, c2, c3 = st.columns(3)
    c1.metric("Position in tree", f"{pos:,}")
    c2.metric("Tree depth (levels)", len(siblings))
    c3.metric("Sibling hashes needed", len(siblings))

    st.markdown("### Step-by-step reconstruction")
    st.caption(
        "At each level we concatenate the current hash with its sibling "
        "(left / right depending on the position parity) **after reversing "
        "the bytes to little-endian**, then take double-SHA256, and "
        "reverse the result back to display order."
    )

    table_rows = []
    for s in steps:
        if s.side == "leaf":
            table_rows.append({
                "Level": 0,
                "Side": "leaf (txid)",
                "Sibling": "—",
                "Hash after step": s.current_be,
            })
        else:
            table_rows.append({
                "Level": s.level,
                "Side": s.side,
                "Sibling": s.sibling_be,
                "Hash after step": s.current_be,
            })
    st.dataframe(table_rows, use_container_width=True, hide_index=True)

    st.markdown("### Verification")
    st.code(
        "computed_root = "
        "double_SHA256( ... double_SHA256(txid_le || sibling0_le) ... )[::-1]\n"
        f"computed_root  = {computed_root}\n"
        f"reported root  = {block['merkle_root']}",
        language="text",
    )

    if matches:
        st.success(
            "✅ The reconstructed root matches the block's Merkle root. "
            f"Transaction `{txid[:16]}…` is **provably included** in "
            f"block #{block['height']}, and therefore committed to by "
            "its Proof of Work."
        )
    else:
        st.error(
            "❌ Mismatch between the reconstructed root and the reported "
            "root. Either the proof is malformed or the implementation "
            "has a bug."
        )

    with st.expander("Why this matters (SPV)"):
        st.markdown(
            "A light client (e.g. a mobile wallet) does not need to "
            "download every block to confirm that a payment was included. "
            "It only needs the **block header** (80 bytes) plus the "
            "**Merkle path** of the transaction it cares about — typically "
            f"~{len(siblings)} hashes in this block, "
            f"or `log₂({len(txids)}) ≈ {len(siblings)}`. "
            "Combined with PoW verification (M2), the receiver can be "
            "confident the transaction was mined without trusting any "
            "single full node. This is **Simplified Payment Verification**, "
            "introduced in Section 8 of the Bitcoin whitepaper."
        )
