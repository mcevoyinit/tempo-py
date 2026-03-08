#!/usr/bin/env python3
"""
03 — Batch Transfers (Atomic Multi-Call)

Demonstrates Tempo's killer feature: batching multiple operations into
a single atomic transaction. All calls succeed or all revert together.
This is built into the transaction format — no smart contract needed.
"""
from tempo_utils import *


def main():
    header("03 · BATCH TRANSFERS")
    w3, account, chain_id = connect()

    section("Setup")
    kv("Sender", account.address)

    # Create 4 recipients with different amounts
    recipients = []
    amounts = [500_000, 1_000_000, 2_500_000, 100_000]  # 0.5, 1.0, 2.5, 0.1
    labels = ["Alice", "Bob", "Carol", "Dave"]

    for label, amount in zip(labels, amounts):
        addr = w3.eth.account.create().address
        recipients.append((label, addr, amount))
        kv(f"{label}", f"{addr[:18]}... → {fmt_amount(amount)} PathUSD")

    total = sum(amounts)
    kv("Total", f"{fmt_amount(total)} PathUSD in 1 atomic tx")

    section("Building Batch Transaction")
    calls = []
    for _, addr, amount in recipients:
        calls.append(
            Call.create(to=PATH_USD, value=0, data=encode_transfer(addr, amount))
        )
    kv("Calls in Batch", len(calls))

    section("Sending Batch")
    sender_before = get_balance(w3, PATH_USD, account.address)
    tx_hash, receipt, _ = send_tempo_tx(w3, account, calls=calls, gas_limit=2_000_000)
    tx_summary(tx_hash, receipt)

    section("Results")
    all_ok = True
    for label, addr, expected in recipients:
        bal = get_balance(w3, PATH_USD, addr)
        ok = bal == expected
        status = "✓" if ok else "✗"
        print(f"  {status} {label}: {fmt_amount(bal)} PathUSD", end="")
        if ok:
            print(" (correct)")
        else:
            print(f" (expected {fmt_amount(expected)})")
            all_ok = False

    sender_after = get_balance(w3, PATH_USD, account.address)
    gas_cost = sender_before - sender_after - total
    kv("Gas Cost", fmt_amount(gas_cost))

    if all_ok:
        success(f"All {len(recipients)} transfers in 1 atomic tx")
    else:
        fail("Some transfers did not match expected amounts")


if __name__ == "__main__":
    main()
