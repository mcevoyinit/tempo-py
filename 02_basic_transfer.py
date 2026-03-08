#!/usr/bin/env python3
"""
02 — Basic TIP-20 Transfer

Demonstrates the fundamental Tempo operation: transferring PathUSD tokens
via a Type 0x76 AA transaction. All value transfers on Tempo go through
TIP-20 token contracts — native ETH transfers are not supported.
"""
from tempo_utils import *


def main():
    header("02 · BASIC TIP-20 TRANSFER")
    w3, account, chain_id = connect()

    section("Setup")
    kv("Chain ID", chain_id)
    kv("Sender", account.address)
    kv("Block", w3.eth.block_number)

    # Generate fresh recipient
    recipient = w3.eth.account.create().address
    transfer_amount = 1_000_000  # 1.0 PathUSD (6 decimals)

    sender_before = get_balance(w3, PATH_USD, account.address)
    recip_before = get_balance(w3, PATH_USD, recipient)

    kv("Recipient", recipient)
    kv("Amount", f"{fmt_amount(transfer_amount)} PathUSD")

    section("Balances Before")
    kv("Sender", fmt_amount(sender_before))
    kv("Recipient", fmt_amount(recip_before))

    section("Sending Transfer")
    calldata = encode_transfer(recipient, transfer_amount)
    tx_hash, receipt, _ = send_tempo_tx(
        w3, account,
        calls=[Call.create(to=PATH_USD, value=0, data=calldata)],
    )
    tx_summary(tx_hash, receipt)

    section("Balances After")
    sender_after = get_balance(w3, PATH_USD, account.address)
    recip_after = get_balance(w3, PATH_USD, recipient)
    kv("Sender", fmt_amount(sender_after))
    kv("Recipient", fmt_amount(recip_after))

    section("Verification")
    if recip_after == transfer_amount:
        success(f"Recipient received exactly {fmt_amount(transfer_amount)} PathUSD")
    else:
        fail(f"Expected {fmt_amount(transfer_amount)}, got {fmt_amount(recip_after)}")

    # Sender lost transfer + gas fees (paid in PathUSD)
    sender_diff = sender_before - sender_after
    gas_cost = sender_diff - transfer_amount
    kv("Gas Cost (PathUSD)", fmt_amount(gas_cost))
    success("Basic transfer complete")


if __name__ == "__main__":
    main()
