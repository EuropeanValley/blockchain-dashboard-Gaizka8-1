"""Bitcoin blockchain client.

Thin wrapper around the public Blockstream REST API
(https://blockstream.info/api). All functions return raw values from the
network so the rest of the dashboard can stay decoupled from the data source.

Run this file directly for a quick sanity check (Milestone 2).
"""

from __future__ import annotations

import time
from typing import Any

import requests

BLOCKSTREAM_BASE = "https://blockstream.info/api"
BLOCKCHAIN_INFO_BASE = "https://api.blockchain.info"
DEFAULT_TIMEOUT = 10
USER_AGENT = "CryptoChainAnalyzerDashboard/1.0 (UAX Cryptography 2025-26)"


def _get(base: str, path: str, *, as_json: bool = True, retries: int = 3) -> Any:
    """GET ``base + path`` with simple retry / back-off."""
    url = f"{base}{path}"
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            r = requests.get(
                url,
                timeout=DEFAULT_TIMEOUT,
                headers={"User-Agent": USER_AGENT},
            )
            r.raise_for_status()
            return r.json() if as_json else r.text
        except (requests.RequestException, ValueError) as exc:
            last_exc = exc
            time.sleep(0.5 * (attempt + 1))
    raise RuntimeError(f"HTTP request failed: {url} ({last_exc})")


def get_tip_height() -> int:
    """Return the height of the most recent block on the chain."""
    return int(_get(BLOCKSTREAM_BASE, "/blocks/tip/height", as_json=False))


def get_block_hash_by_height(height: int) -> str:
    """Return the block hash for the given height."""
    return _get(BLOCKSTREAM_BASE, f"/block-height/{height}", as_json=False).strip()


def get_block(block_hash: str) -> dict:
    """Full block metadata (height, hash, difficulty, nonce, bits, ...)."""
    return _get(BLOCKSTREAM_BASE, f"/block/{block_hash}")


def get_block_header_hex(block_hash: str) -> str:
    """The 80-byte block header as a hex string."""
    return _get(BLOCKSTREAM_BASE, f"/block/{block_hash}/header", as_json=False).strip()


def get_recent_blocks(n: int = 50) -> list[dict]:
    """Return the last ``n`` blocks ordered from newest to oldest."""
    blocks: list[dict] = []
    cursor = get_tip_height()
    while len(blocks) < n:
        page = _get(BLOCKSTREAM_BASE, f"/blocks/{cursor}")
        if not page:
            break
        blocks.extend(page)
        cursor = page[-1]["height"] - 1
        if cursor < 0:
            break
    return blocks[:n]


def get_block_at_height(height: int) -> dict:
    """Convenience: hash lookup + full block metadata."""
    return get_block(get_block_hash_by_height(height))


def get_latest_block() -> dict:
    """Backwards-compatible helper: fetches the current chain tip."""
    return get_block_at_height(get_tip_height())


def get_block_txids(block_hash: str) -> list[str]:
    """Return the list of all transaction IDs in the given block.

    Used by M5 to let the user pick a transaction whose Merkle proof we
    will then reconstruct manually.
    """
    return _get(BLOCKSTREAM_BASE, f"/block/{block_hash}/txids")


def get_btc_price_usd() -> float:
    """Spot BTC/USD price from the blockchain.info ticker.

    Used by M6 to convert the network's energy expenditure into a USD
    figure. Falls back to a hard-coded approximation if the API is down.
    """
    try:
        data = _get(BLOCKCHAIN_INFO_BASE, "/ticker")
        return float(data["USD"]["last"])
    except Exception:  # noqa: BLE001
        return 60_000.0  # safe fallback so the dashboard keeps running


def get_merkle_proof(txid: str) -> dict:
    """Return the Merkle inclusion proof of a transaction.

    The Blockstream response has the shape::

        {
            "block_height": 948592,
            "merkle":       ["sibling1_hex", "sibling2_hex", ...],
            "pos":          27   # leaf index inside the tree
        }

    where each sibling hash is in *display* (big-endian) byte order.
    """
    return _get(BLOCKSTREAM_BASE, f"/tx/{txid}/merkle-proof")


def get_difficulty_history(n_points: int = 100) -> list[dict]:
    """Difficulty time-series from blockchain.info charts API.

    Returns a list of ``{"x": unix_ts, "y": difficulty}`` dicts.
    """
    timespan = "1year" if n_points <= 365 else "all"
    data = _get(
        BLOCKCHAIN_INFO_BASE,
        f"/charts/difficulty?timespan={timespan}&format=json&cors=true",
    )
    return data.get("values", [])[-n_points:]


def _print_latest_block() -> None:
    """First API call - prints the latest block to the console."""
    block = get_latest_block()
    print(
        "Height:     {height}\n"
        "Hash:       {id}\n"
        "Difficulty: {difficulty}\n"
        "Nonce:      {nonce}\n"
        "Bits:       {bits}\n"
        "Tx count:   {tx_count}".format(**block)
    )
    # Observation: the hash starts with many leading zeros -> Proof of Work.
    # The 'bits' field is a compact encoding of the target threshold
    # (Section 6 of the notes). The double-SHA256 of the 80-byte header
    # must be numerically below that target for the block to be valid.


if __name__ == "__main__":
    _print_latest_block()
