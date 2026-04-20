import requests

# Milestone 2 - First API call: fetch the latest Bitcoin block from Blockstream
tip = requests.get("https://blockstream.info/api/blocks/tip/height").text
block_hash = requests.get(f"https://blockstream.info/api/block-height/{tip}").text
block = requests.get(f"https://blockstream.info/api/block/{block_hash}").json()
print(f"Height:     {block['height']}\nHash:       {block['id']}\nDifficulty: {block['difficulty']}\nNonce:      {block['nonce']}\nBits:       {block['bits']}\nTx count:   {block['tx_count']}")
# Observation: the hash starts with many leading zeros -> that is the Proof of Work.
# The 'bits' field is a compact encoding of the target threshold (Section 6 of the notes).
# The SHA-256 of the block header must be numerically below that target for the block to be valid.
