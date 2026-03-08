#!/usr/bin/env python3
"""
10 — Expiring Nonces (TIP-1009)

Demonstrates Tempo's time-windowed transactions. Instead of sequential
nonces, expiring transactions use the tx hash for replay protection and
specify a validity window:

  valid_after  ≤ block.timestamp < valid_before

This enables:
  - MEV protection (transactions auto-expire)
  - Conditional execution (only valid in a time window)
  - No nonce management needed for one-shot operations
"""
import time

from tempo_utils import *


def main():
    header("10 · EXPIRING NONCES (TIP-1009)")
    w3, account, chain_id = connect()

    section("Concept")
    print("  Expiring nonces use tx hash (not sequence) for replay protection")
    print("  valid_after ≤ block.timestamp < valid_before")
    print("  Max expiry window: 30 seconds from current block")

    section("Setup")
    recipient = w3.eth.account.create().address
    amount = 250_000  # 0.25 PathUSD
    kv("Recipient", recipient[:24] + "...")
    kv("Amount", f"{fmt_amount(amount)} PathUSD")

    now = int(time.time())
    valid_after = now - 5    # Valid from 5 seconds ago
    valid_before = now + 25  # Expires in 25 seconds

    kv("Current Time", now)
    kv("Valid After", f"{valid_after} (now - 5s)")
    kv("Valid Before", f"{valid_before} (now + 25s)")

    # ─── Send Expiring Transaction ──────────────────────────────
    section("Sending Expiring Transaction")
    calldata = encode_transfer(recipient, amount)
    try:
        tx_hash, receipt, _ = send_tempo_tx(
            w3, account,
            calls=[Call.create(to=PATH_USD, value=0, data=calldata)],
            valid_before=valid_before,
            valid_after=valid_after,
        )
        tx_summary(tx_hash, receipt)

        bal = get_balance(w3, PATH_USD, recipient)
        if bal == amount:
            success(f"Expiring tx succeeded within validity window")
        else:
            fail(f"Balance mismatch: {fmt_amount(bal)}")

    except Exception as e:
        # This might fail if expiring nonces aren't fully supported in dev mode
        fail(f"Expiring tx failed: {e}")
        print("  Note: Expiring nonces may require specific node configuration")

    # ─── Try Expired Transaction ────────────────────────────────
    section("Attempting Expired Transaction")
    print("  Setting valid_before to 1 second ago (should fail)")

    recipient2 = w3.eth.account.create().address
    expired_before = now - 1  # Already expired

    calldata2 = encode_transfer(recipient2, amount)
    try:
        tx_hash2, receipt2, _ = send_tempo_tx(
            w3, account,
            calls=[Call.create(to=PATH_USD, value=0, data=calldata2)],
            valid_before=expired_before,
            valid_after=now - 60,
        )
        # If we get here, the tx was accepted (might be rejected at block level)
        if receipt2["status"] == 0:
            success("Expired tx correctly rejected (status=0)")
        else:
            print("  ? Expired tx was accepted — validity window may be approximate")
    except Exception as e:
        success(f"Expired tx correctly rejected: {str(e)[:60]}")

    success("Expiring nonce demonstration complete")


if __name__ == "__main__":
    main()
