"""Cryptographic helpers shared by M1, M2 and M3.

Direct application of Section 6 of the Blockchain notes (Topic 7):
the *bits* compact encoding, the SHA-256 double hash of the 80-byte
block header, and the leading-zero counting that defines Proof of Work.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

# Maximum target accepted by the Bitcoin protocol (difficulty 1).
MAX_TARGET = 0x00000000FFFF0000000000000000000000000000000000000000000000000000


# ---------------------------------------------------------------------------
# bits <-> target  (compact representation)
# ---------------------------------------------------------------------------

def bits_to_target(bits: int) -> int:
    """Decode the 32-bit compact "bits" field into the full 256-bit target.

    Encoding: target = mantissa * 256**(exponent - 3).
    """
    exponent = bits >> 24
    mantissa = bits & 0x007FFFFF
    if exponent <= 3:
        return mantissa >> (8 * (3 - exponent))
    return mantissa << (8 * (exponent - 3))


def target_to_difficulty(target: int) -> float:
    return MAX_TARGET / target


def difficulty_to_target(difficulty: float) -> int:
    return int(MAX_TARGET / difficulty)


def leading_zero_bits(hex_hash: str) -> int:
    """Count the leading zero *bits* in a hex-encoded hash."""
    n = int(hex_hash, 16)
    if n == 0:
        return 256
    return 256 - n.bit_length()


# ---------------------------------------------------------------------------
# block header parsing + Proof of Work verification
# ---------------------------------------------------------------------------

@dataclass
class BlockHeader:
    version: int
    prev_hash: str          # display order (big-endian)
    merkle_root: str        # display order (big-endian)
    timestamp: int
    bits: int
    nonce: int
    raw_hex: str
    hash_hex: str
    target: int

    @property
    def hash_int(self) -> int:
        return int(self.hash_hex, 16)

    @property
    def difficulty(self) -> float:
        return target_to_difficulty(self.target)

    @property
    def leading_zero_bits(self) -> int:
        return leading_zero_bits(self.hash_hex)

    @property
    def pow_valid(self) -> bool:
        """The PoW rule: hash < target."""
        return self.hash_int < self.target


def _le_hex(b: bytes) -> str:
    """Bytes in little-endian display order (= reverse-bytes hex)."""
    return b[::-1].hex()


def parse_header(header_hex: str) -> BlockHeader:
    """Parse the 80-byte hex header returned by Blockstream.

    Bitcoin stores header fields little-endian. We convert them back
    to the human-readable big-endian display form.
    """
    raw = bytes.fromhex(header_hex)
    if len(raw) != 80:
        raise ValueError(f"Header must be exactly 80 bytes, got {len(raw)}")

    version = int.from_bytes(raw[0:4], "little")
    prev_hash_be = _le_hex(raw[4:36])
    merkle_root_be = _le_hex(raw[36:68])
    timestamp = int.from_bytes(raw[68:72], "little")
    bits = int.from_bytes(raw[72:76], "little")
    nonce = int.from_bytes(raw[76:80], "little")

    # Bitcoin block hash = double-SHA256 of the 80-byte header,
    # then reverse-bytes for display (Satoshi-endian convention).
    digest = hashlib.sha256(hashlib.sha256(raw).digest()).digest()
    block_hash_be = _le_hex(digest)

    return BlockHeader(
        version=version,
        prev_hash=prev_hash_be,
        merkle_root=merkle_root_be,
        timestamp=timestamp,
        bits=bits,
        nonce=nonce,
        raw_hex=header_hex,
        hash_hex=block_hash_be,
        target=bits_to_target(bits),
    )


# ---------------------------------------------------------------------------
# derived metric: estimated network hash rate
# ---------------------------------------------------------------------------

def estimated_hashrate(difficulty: float, avg_block_time: float = 600.0) -> float:
    """Hash rate estimate in hashes per second.

    difficulty 1 means an expected 2**32 hashes per block; multiply by
    current difficulty and divide by observed average block time.
    """
    return difficulty * (2 ** 32) / max(avg_block_time, 1e-9)


def humanize_hashrate(hps: float) -> str:
    units = [(1e18, "EH/s"), (1e15, "PH/s"), (1e12, "TH/s"), (1e9, "GH/s"), (1e6, "MH/s")]
    for factor, suffix in units:
        if hps >= factor:
            return f"{hps / factor:.2f} {suffix}"
    return f"{hps:.0f} H/s"


# ---------------------------------------------------------------------------
# Merkle proof verification (used by M5)
# ---------------------------------------------------------------------------

def _double_sha256(b: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()


@dataclass
class MerkleStep:
    level: int
    side: str           # "leaf", "left", "right"
    sibling_be: str     # display-form sibling hash, "" for the leaf
    current_be: str     # display-form hash AFTER this step


def verify_merkle_proof(
    txid_be: str,
    siblings_be: list[str],
    pos: int,
) -> tuple[str, list[MerkleStep]]:
    """Recompute a Merkle root step by step from a leaf.

    Bitcoin Merkle quirks (Section 7 of the notes):

    * Leaves and internal nodes are hashed with **double-SHA256**.
    * Hashes are concatenated in their *internal* (little-endian) byte
      order. Block explorers display them reversed, so we have to flip
      the bytes before feeding them to SHA-256 and flip the result back.
    * At each level, ``pos`` tells us whether ``current`` is the left
      child (even index → sibling on the right) or the right child
      (odd index → sibling on the left).

    Returns ``(computed_root_be, steps)`` so the dashboard can render
    each intermediate computation.
    """
    current = bytes.fromhex(txid_be)[::-1]  # → internal LE bytes

    steps: list[MerkleStep] = [
        MerkleStep(level=0, side="leaf", sibling_be="", current_be=txid_be)
    ]

    for level, sibling_hex in enumerate(siblings_be, start=1):
        sibling = bytes.fromhex(sibling_hex)[::-1]
        if pos % 2 == 0:
            combined = current + sibling          # left || right
            side = "right"
        else:
            combined = sibling + current          # left || right (we are right)
            side = "left"
        current = _double_sha256(combined)
        steps.append(
            MerkleStep(
                level=level,
                side=f"sibling on {side}",
                sibling_be=sibling_hex,
                current_be=current[::-1].hex(),
            )
        )
        pos //= 2

    return current[::-1].hex(), steps
