#!/usr/bin/env python3
"""
04 — Transfer with Memo

Demonstrates attaching a 32-byte memo to a TIP-20 transfer.
Memos enable payment tracking, invoice references, and on-chain metadata
without requiring separate data fields or smart contracts.

Function: transferWithMemo(address to, uint256 amount, bytes32 memo)
"""
from tempo_utils import *


def main():
    header("04 · TRANSFER WITH MEMO")
    w3, account, chain_id = connect()

    section("Setup")
    recipient = w3.eth.account.create().address
    amount = 750_000  # 0.75 PathUSD
    memo_text = "INV-2026-0042"
    memo = Web3.keccak(text=memo_text)  # 32-byte hash of the reference

    kv("Sender", account.address)
    kv("Recipient", recipient[:24] + "...")
    kv("Amount", f"{fmt_amount(amount)} PathUSD")
    kv("Memo Text", memo_text)
    kv("Memo Hash", memo.hex()[:20] + "...")

    section("Sending Transfer with Memo")
    calldata = encode_transfer_with_memo(recipient, amount, memo)
    tx_hash, receipt, _ = send_tempo_tx(
        w3, account,
        calls=[Call.create(to=PATH_USD, value=0, data=calldata)],
    )
    tx_summary(tx_hash, receipt)

    section("Receipt Logs")
    for i, log in enumerate(receipt.get("logs", [])):
        topics = log.get("topics", [])
        if len(topics) > 0:
            # TransferWithMemo has 3 indexed topics: event sig, from, to
            event_sig = topics[0].hex() if topics[0] else ""
            print(f"  Log {i}: {len(topics)} topics, {len(log.get('data', b''))} bytes data")
            if len(topics) >= 3:
                from_addr = "0x" + topics[1].hex()[-40:]
                to_addr = "0x" + topics[2].hex()[-40:]
                print(f"         from: {from_addr[:18]}...")
                print(f"         to:   {to_addr[:18]}...")

    section("Verification")
    bal = get_balance(w3, PATH_USD, recipient)
    if bal == amount:
        success(f"Recipient received {fmt_amount(amount)} PathUSD with memo")
    else:
        fail(f"Balance mismatch: {fmt_amount(bal)} vs expected {fmt_amount(amount)}")

    success("Memo transfer complete — reference trackable on-chain")


if __name__ == "__main__":
    main()
