#!/usr/bin/env python3
"""
12 — Fee AMM (Custom Fee Tokens)

Demonstrates using a non-default stablecoin to pay transaction fees.
When a user's fee token differs from the validator's preferred token,
the Fee AMM automatically swaps between them.

Flow:
  1. Create a new TIP-20 token
  2. Mint tokens to user
  3. Add liquidity to the Fee AMM pool (new_token ↔ PathUSD)
  4. Set user's fee token to the new token
  5. Execute a transaction paying gas in the new token
"""
import os
from tempo_utils import *


def create_token(w3, account, name, symbol):
    """Create a new TIP-20 token and return its address."""
    salt = Web3.keccak(text=f"{name}-{os.getpid()}-fee")
    calldata = encode_create_token(name, symbol, "USD", PATH_USD, account.address, salt)
    tx_hash, receipt, _ = send_tempo_tx(
        w3, account,
        calls=[Call.create(to=TIP20_FACTORY, value=0, data=calldata)],
        gas_limit=3_000_000,
    )
    for log in receipt.get("logs", []):
        topics = log.get("topics", [])
        if len(topics) >= 2:
            addr_hex = "0x" + topics[1].hex()[-40:]
            candidate = Web3.to_checksum_address(addr_hex)
            if candidate.lower().startswith("0x20c0"):
                return candidate
    return None


def main():
    header("12 · FEE AMM (CUSTOM FEE TOKENS)")
    w3, account, chain_id = connect()

    section("1. Create Custom Fee Token")
    fee_token = create_token(w3, account, "FeeDemo", "FEED")
    if not fee_token:
        fail("Could not create fee token")
        return

    kv("New Token", fee_token)
    kv("Name", read_string(w3, fee_token, "name"))

    # ─── Grant ISSUER_ROLE and mint ─────────────────────────────
    section("2. Mint Custom Tokens")
    mint_amount = 100_000_000_000_000  # Large amount for fees + liquidity

    calls = [
        Call.create(to=fee_token, value=0,
                    data=encode_grant_role(ISSUER_ROLE, account.address)),
        Call.create(to=fee_token, value=0,
                    data=encode_mint(account.address, mint_amount)),
    ]
    tx_hash, receipt, _ = send_tempo_tx(w3, account, calls=calls)
    kv("Minted", fmt_amount(mint_amount))
    kv("Status", "SUCCESS" if receipt["status"] == 1 else "FAILED")

    bal = get_balance(w3, fee_token, account.address)
    kv("Token Balance", fmt_amount(bal))

    # ─── Approve Fee Manager ────────────────────────────────────
    section("3. Approve Fee Manager for Swaps")
    max_approve = (2**256) - 1

    # Fee Manager uses system_transfer_from (privileged), but approve anyway
    calls = [
        Call.create(to=fee_token, value=0,
                    data=encode_approve(TIP_FEE_MANAGER, max_approve)),
        Call.create(to=PATH_USD, value=0,
                    data=encode_approve(TIP_FEE_MANAGER, max_approve)),
    ]
    tx_hash, receipt, _ = send_tempo_tx(w3, account, calls=calls)
    kv("Approved", "FeeDemo + PathUSD → Fee Manager")
    kv("Status", "SUCCESS" if receipt["status"] == 1 else "FAILED")

    # ─── Add Liquidity ──────────────────────────────────────────
    section("4. Add AMM Liquidity")
    liq_amount = 10_000_000_000  # 10,000 of each token

    calldata = encode_add_liquidity(
        fee_token, PATH_USD, liq_amount, account.address,
    )
    try:
        tx_hash, receipt, _ = send_tempo_tx(
            w3, account,
            calls=[Call.create(to=TIP_FEE_MANAGER, value=0, data=calldata)],
        )
        kv("Liquidity", f"{fmt_amount(liq_amount)} PathUSD deposited")
        tx_summary(tx_hash, receipt)
    except Exception as e:
        fail(f"Add liquidity failed: {e}")
        print("  Note: Fee AMM may require specific pool configuration")
        return

    # ─── Set User Fee Token ─────────────────────────────────────
    section("5. Set User Fee Token")
    calldata = encode_set_user_token(fee_token)
    try:
        tx_hash, receipt, _ = send_tempo_tx(
            w3, account,
            calls=[Call.create(to=TIP_FEE_MANAGER, value=0, data=calldata)],
        )
        kv("User Fee Token", fee_token[:24] + "...")
        tx_summary(tx_hash, receipt)
    except Exception as e:
        fail(f"Set fee token failed: {e}")
        return

    # ─── Execute Transaction with Custom Fee Token ──────────────
    section("6. Transfer Using Custom Fee Token for Gas")
    recipient = w3.eth.account.create().address
    send_amount = 500_000  # 0.5 PathUSD

    fee_bal_before = get_balance(w3, fee_token, account.address)
    pusd_bal_before = get_balance(w3, PATH_USD, account.address)

    calldata = encode_transfer(recipient, send_amount)
    try:
        tx_hash, receipt, _ = send_tempo_tx(
            w3, account,
            calls=[Call.create(to=PATH_USD, value=0, data=calldata)],
            fee_token=fee_token,
        )
        tx_summary(tx_hash, receipt)

        fee_bal_after = get_balance(w3, fee_token, account.address)
        pusd_bal_after = get_balance(w3, PATH_USD, account.address)

        fee_spent = fee_bal_before - fee_bal_after
        pusd_spent = pusd_bal_before - pusd_bal_after

        kv("FeeDemo Spent (gas)", fmt_amount(fee_spent))
        kv("PathUSD Spent", fmt_amount(pusd_spent))

        recip_bal = get_balance(w3, PATH_USD, recipient)
        if recip_bal == send_amount:
            success("Transfer succeeded paying gas in custom fee token")
        else:
            fail(f"Transfer amount mismatch: {fmt_amount(recip_bal)}")

    except Exception as e:
        fail(f"Custom fee token tx failed: {e}")
        print("  This may fail if the Fee AMM pool doesn't have enough liquidity")
        print("  or if the validator doesn't accept the fee token swap")

    # ─── Reset Fee Token to Default ─────────────────────────────
    section("7. Reset to Default Fee Token")
    calldata = encode_set_user_token(PATH_USD)
    try:
        tx_hash, receipt, _ = send_tempo_tx(
            w3, account,
            calls=[Call.create(to=TIP_FEE_MANAGER, value=0, data=calldata)],
        )
        success("Reset to PathUSD as fee token")
    except Exception as e:
        print(f"  Reset failed: {e}")

    success("Fee AMM demonstration complete")


if __name__ == "__main__":
    main()
