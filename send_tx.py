"""
Send Tempo AA transactions on our local 2-node network.

Node 1 (consensus): http://localhost:9545
Node 2 (follower):  http://localhost:9546

Tempo is a stablecoin-only chain — all transfers go through TIP-20 tokens.
Gas is paid in stablecoins. Using PathUSD (DEFAULT_FEE_TOKEN) avoids AMM.
"""
import sys
import time

sys.path.insert(0, "/Users/mcevoyinit/eric/pytempo")

from web3 import Web3

from pytempo import Call, TempoTransaction

# --- Config ---
NODE1_RPC = "http://localhost:9545"
NODE2_RPC = "http://localhost:9546"

# Foundry/Hardhat default dev account #0
DEV_PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"

# PathUSD = DEFAULT_FEE_TOKEN (validator accepts directly, no AMM liquidity needed)
PATH_USD = Web3.to_checksum_address("0x20c0000000000000000000000000000000000000")

# ERC-20 / TIP-20 selectors
TRANSFER_SIG = Web3.keccak(text="transfer(address,uint256)")[:4]
BALANCE_SIG = Web3.keccak(text="balanceOf(address)")[:4]


def get_token_balance(w3, token, account):
    addr_padded = account[2:].lower().zfill(64)
    calldata = "0x" + BALANCE_SIG.hex() + addr_padded
    result = w3.eth.call({"to": token, "data": calldata})
    return int(result.hex(), 16)


def encode_transfer(recipient, amount):
    addr_padded = recipient[2:].lower().zfill(64)
    amt_hex = hex(amount)[2:].zfill(64)
    return bytes.fromhex(TRANSFER_SIG.hex() + addr_padded + amt_hex)


def main():
    w3 = Web3(Web3.HTTPProvider(NODE1_RPC))
    assert w3.is_connected(), "Cannot connect to Node 1"

    account = w3.eth.account.from_key(DEV_PRIVATE_KEY)
    chain_id = w3.eth.chain_id
    gas_price = w3.eth.gas_price or 20_000_000_000

    print("=" * 60)
    print("TEMPO LOCAL NETWORK - AA TRANSACTION TEST")
    print("=" * 60)
    print(f"Chain ID:     {chain_id}")
    print(f"Sender:       {account.address}")
    print(f"Block:        {w3.eth.block_number}")
    print(f"Gas price:    {gas_price}")

    # Generate a fresh recipient
    recipient_acct = w3.eth.account.create()
    recipient = recipient_acct.address
    print(f"Recipient:    {recipient}")

    # Check PathUSD balances
    sender_bal = get_token_balance(w3, PATH_USD, account.address)
    print(f"\nPathUSD balances:")
    print(f"  Sender:    {sender_bal}")
    print(f"  Recipient: {get_token_balance(w3, PATH_USD, recipient)}")

    # === Tempo AA Transaction (Type 0x76) - Transfer PathUSD ===
    print("\n" + "=" * 60)
    print("TX 1: Tempo AA Transaction (Type 0x76)")
    print("Transfer 1000 PathUSD to recipient")
    print("=" * 60)

    nonce = w3.eth.get_transaction_count(account.address)
    transfer_amount = 1000
    calldata = encode_transfer(recipient, transfer_amount)

    tx1 = TempoTransaction.create(
        chain_id=chain_id,
        gas_limit=1_000_000,
        max_fee_per_gas=gas_price * 3,
        max_priority_fee_per_gas=gas_price,
        nonce=nonce,
        fee_token=PATH_USD,  # DEFAULT_FEE_TOKEN — validator accepts directly
        calls=(
            Call.create(to=PATH_USD, value=0, data=calldata),
        ),
    )

    signed_tx1 = tx1.sign(DEV_PRIVATE_KEY)
    tx_hash1 = w3.eth.send_raw_transaction(signed_tx1.encode())
    print(f"Tx hash:  {tx_hash1.hex()}")

    receipt1 = w3.eth.wait_for_transaction_receipt(tx_hash1, timeout=30)
    print(f"Status:   {'SUCCESS' if receipt1['status'] == 1 else 'FAILED'}")
    print(f"Block:    {receipt1['blockNumber']}")
    print(f"Gas used: {receipt1['gasUsed']}")

    r_bal1 = get_token_balance(w3, PATH_USD, recipient)
    print(f"Recipient PathUSD: {r_bal1}")

    # === TX 2: Batched AA Transaction — multiple transfers in one ===
    print("\n" + "=" * 60)
    print("TX 2: Batched AA Transaction (2 transfers in 1 tx)")
    print("=" * 60)

    nonce2 = w3.eth.get_transaction_count(account.address)
    recipient2 = w3.eth.account.create().address
    amount_a = 5000
    amount_b = 3000

    tx2 = TempoTransaction.create(
        chain_id=chain_id,
        gas_limit=1_000_000,
        max_fee_per_gas=gas_price * 3,
        max_priority_fee_per_gas=gas_price,
        nonce=nonce2,
        fee_token=PATH_USD,
        calls=(
            Call.create(to=PATH_USD, value=0, data=encode_transfer(recipient, amount_a)),
            Call.create(to=PATH_USD, value=0, data=encode_transfer(recipient2, amount_b)),
        ),
    )

    signed_tx2 = tx2.sign(DEV_PRIVATE_KEY)
    tx_hash2 = w3.eth.send_raw_transaction(signed_tx2.encode())
    print(f"Tx hash:  {tx_hash2.hex()}")

    receipt2 = w3.eth.wait_for_transaction_receipt(tx_hash2, timeout=30)
    print(f"Status:   {'SUCCESS' if receipt2['status'] == 1 else 'FAILED'}")
    print(f"Block:    {receipt2['blockNumber']}")
    print(f"Gas used: {receipt2['gasUsed']}")

    # === Final balances ===
    print("\n" + "=" * 60)
    print("FINAL BALANCES")
    print("=" * 60)
    s_final = get_token_balance(w3, PATH_USD, account.address)
    r1_final = get_token_balance(w3, PATH_USD, recipient)
    r2_final = get_token_balance(w3, PATH_USD, recipient2)
    print(f"Sender PathUSD:     {s_final}")
    print(f"Recipient 1:        {r1_final} (expected {transfer_amount + amount_a})")
    print(f"Recipient 2:        {r2_final} (expected {amount_b})")

    # === Node 2 verification ===
    print("\n" + "=" * 60)
    print("NODE 2 VERIFICATION")
    print("=" * 60)
    w3_node2 = Web3(Web3.HTTPProvider(NODE2_RPC))
    if w3_node2.is_connected():
        n2_block = w3_node2.eth.block_number
        n1_block = w3.eth.block_number
        print(f"Node 1 block: {n1_block}")
        print(f"Node 2 block: {n2_block}")
        if n2_block > 0:
            try:
                r2_bal = get_token_balance(w3_node2, PATH_USD, recipient)
                print(f"Recipient 1 on Node 2: {r2_bal}")
            except Exception as e:
                print(f"Node 2 query: {e}")
            try:
                r = w3_node2.eth.get_transaction_receipt(tx_hash2)
                print(f"Batch tx on Node 2: FOUND (block {r['blockNumber']})")
            except Exception:
                print("Batch tx on Node 2: NOT YET SYNCED")
        else:
            print("Node 2 still syncing...")
    else:
        print("Node 2 not reachable")

    print("\nDone!")


if __name__ == "__main__":
    main()
