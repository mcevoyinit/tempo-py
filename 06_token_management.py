#!/usr/bin/env python3
"""
06 — Token Management (Mint, Burn, Roles, Pause)

Demonstrates TIP-20 admin operations:
  - Grant ISSUER_ROLE to an account
  - Mint tokens (requires ISSUER_ROLE)
  - Burn tokens (requires ISSUER_ROLE)
  - Grant PAUSE_ROLE
  - Pause/unpause token

Uses the dev account which is DEFAULT_ADMIN on PathUSD.
"""
import os
from tempo_utils import *


def create_demo_token(w3, account):
    """Create a fresh token for management demos."""
    salt = Web3.keccak(text="mgmt-demo-" + str(os.getpid()))
    calldata = encode_create_token(
        "MgmtDemo", "MGMT", "USD", PATH_USD, account.address, salt,
    )
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
    header("06 · TOKEN MANAGEMENT")
    w3, account, chain_id = connect()

    section("Creating Demo Token")
    token = create_demo_token(w3, account)
    if not token:
        fail("Could not create demo token")
        return
    kv("Token", token)
    kv("Name", read_string(w3, token, "name"))

    # ─── Grant ISSUER_ROLE ──────────────────────────────────────
    section("1. Grant ISSUER_ROLE")
    kv("Granting to", account.address[:24] + "...")

    calldata = encode_grant_role(ISSUER_ROLE, account.address)
    tx_hash, receipt, _ = send_tempo_tx(
        w3, account,
        calls=[Call.create(to=token, value=0, data=calldata)],
    )
    tx_summary(tx_hash, receipt)

    # Verify role
    raw = call_view(w3, token, encode_has_role(ISSUER_ROLE, account.address))
    has_issuer = abi_decode(["bool"], raw)[0] if raw else False
    kv("Has ISSUER_ROLE", has_issuer)

    # ─── Mint Tokens ────────────────────────────────────────────
    section("2. Mint Tokens")
    recipient = w3.eth.account.create().address
    mint_amount = 10_000_000_000  # 10,000 tokens

    kv("Mint To", recipient[:24] + "...")
    kv("Amount", fmt_amount(mint_amount))

    calldata = encode_mint(recipient, mint_amount)
    tx_hash, receipt, _ = send_tempo_tx(
        w3, account,
        calls=[Call.create(to=token, value=0, data=calldata)],
    )
    tx_summary(tx_hash, receipt)

    bal = get_balance(w3, token, recipient)
    supply = read_uint256(w3, token, "totalSupply")
    kv("Recipient Balance", fmt_amount(bal))
    kv("Total Supply", fmt_amount(supply))

    if bal == mint_amount:
        success(f"Minted {fmt_amount(mint_amount)} tokens")
    else:
        fail("Mint amount mismatch")

    # ─── Mint to Self & Burn ────────────────────────────────────
    section("3. Burn Tokens")
    burn_amount = 5_000_000_000  # 5,000 tokens

    # First mint to self so we can burn
    calldata_mint = encode_mint(account.address, burn_amount)
    send_tempo_tx(
        w3, account,
        calls=[Call.create(to=token, value=0, data=calldata_mint)],
    )

    self_bal_before = get_balance(w3, token, account.address)
    kv("Self Balance Before", fmt_amount(self_bal_before))

    calldata_burn = encode_burn(burn_amount)
    tx_hash, receipt, _ = send_tempo_tx(
        w3, account,
        calls=[Call.create(to=token, value=0, data=calldata_burn)],
    )
    tx_summary(tx_hash, receipt)

    self_bal_after = get_balance(w3, token, account.address)
    supply_after = read_uint256(w3, token, "totalSupply")
    kv("Self Balance After", fmt_amount(self_bal_after))
    kv("Total Supply After", fmt_amount(supply_after))
    success(f"Burned {fmt_amount(burn_amount)} tokens")

    # ─── Pause / Unpause ────────────────────────────────────────
    section("4. Pause & Unpause Token")

    # Grant PAUSE_ROLE and UNPAUSE_ROLE
    calls = [
        Call.create(to=token, value=0, data=encode_grant_role(PAUSE_ROLE, account.address)),
        Call.create(to=token, value=0, data=encode_grant_role(UNPAUSE_ROLE, account.address)),
    ]
    send_tempo_tx(w3, account, calls=calls)

    # Pause
    tx_hash, receipt, _ = send_tempo_tx(
        w3, account,
        calls=[Call.create(to=token, value=0, data=encode_pause())],
    )
    paused = read_bool(w3, token, "paused")
    kv("Paused", paused)
    if paused:
        success("Token paused — transfers blocked")
    else:
        fail("Token should be paused")

    # Unpause
    tx_hash, receipt, _ = send_tempo_tx(
        w3, account,
        calls=[Call.create(to=token, value=0, data=encode_unpause())],
    )
    paused = read_bool(w3, token, "paused")
    kv("Paused", paused)
    if not paused:
        success("Token unpaused — transfers restored")
    else:
        fail("Token should be unpaused")

    section("Summary")
    success("Demonstrated: grant roles, mint, burn, pause, unpause")


if __name__ == "__main__":
    main()
