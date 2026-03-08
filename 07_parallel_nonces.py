#!/usr/bin/env python3
"""
07 — Parallel Nonces (2D Nonce System)

Demonstrates Tempo's parallelizable nonce system. Unlike Ethereum's single
sequential nonce, Tempo uses a 2D nonce scheme:

  - nonce_key=0:  Protocol nonce (sequential, like Ethereum)
  - nonce_key=1+: User nonces (independent sequences, parallel execution)

Transactions with different nonce_keys can execute in any order, enabling
parallel transaction submission for high-throughput accounts.
"""
from tempo_utils import *


def main():
    header("07 · PARALLEL NONCES")
    w3, account, chain_id = connect()

    section("2D Nonce System Explained")
    print("  Protocol nonce (key=0): Sequential, like Ethereum")
    print("  User nonce (key=1+):    Independent, parallel execution")
    print("  Each key maintains its own nonce counter")

    section("Current Nonce State")
    protocol_nonce = w3.eth.get_transaction_count(account.address)
    kv("Protocol Nonce (key=0)", protocol_nonce)

    # Create 3 recipients
    recipients = [w3.eth.account.create().address for _ in range(3)]
    amounts = [100_000, 200_000, 300_000]  # 0.1, 0.2, 0.3 PathUSD
    nonce_keys = [1, 2, 3]

    section("Sending 3 Parallel Transactions")
    print("  Each uses a different nonce_key → independent sequences")
    print("  All can be mined in any order or same block\n")

    results = []
    for i, (addr, amount, nk) in enumerate(zip(recipients, amounts, nonce_keys)):
        label = f"TX {i+1} (nonce_key={nk})"
        calldata = encode_transfer(addr, amount)
        try:
            tx_hash, receipt, _ = send_tempo_tx(
                w3, account,
                calls=[Call.create(to=PATH_USD, value=0, data=calldata)],
                nonce_key=nk,
                nonce=0,  # First tx in each key's sequence
            )
            status = "SUCCESS" if receipt["status"] == 1 else "FAILED"
            results.append((label, tx_hash, receipt, addr, amount, True))
            print(f"  ✓ {label}: {status} (block {receipt['blockNumber']})")
        except Exception as e:
            results.append((label, None, None, addr, amount, False))
            print(f"  ✗ {label}: {e}")

    section("Verification")
    for label, tx_hash, receipt, addr, expected, ok in results:
        if ok:
            bal = get_balance(w3, PATH_USD, addr)
            match = "✓" if bal == expected else "✗"
            print(f"  {match} {label}: {fmt_amount(bal)} PathUSD (expected {fmt_amount(expected)})")

    # Now send a 2nd tx on nonce_key=1 to show the sequence continues
    section("Continuing Sequence on nonce_key=1")
    extra_recipient = w3.eth.account.create().address
    extra_amount = 150_000

    calldata = encode_transfer(extra_recipient, extra_amount)
    try:
        tx_hash, receipt, _ = send_tempo_tx(
            w3, account,
            calls=[Call.create(to=PATH_USD, value=0, data=calldata)],
            nonce_key=1,
            nonce=1,  # Second tx in key=1's sequence
        )
        kv("Status", "SUCCESS" if receipt["status"] == 1 else "FAILED")
        kv("Block", receipt["blockNumber"])
        bal = get_balance(w3, PATH_USD, extra_recipient)
        kv("Balance", fmt_amount(bal))
        success("nonce_key=1 sequence: nonce 0 → 1 (independent of other keys)")
    except Exception as e:
        fail(f"Second tx on key=1: {e}")

    section("Updated Protocol Nonce")
    new_protocol_nonce = w3.eth.get_transaction_count(account.address)
    kv("Protocol Nonce (key=0)", new_protocol_nonce)
    print("  Note: Protocol nonce unchanged — parallel txs use separate keys")

    success("Parallel nonce demonstration complete")


if __name__ == "__main__":
    main()
