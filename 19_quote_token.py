#!/usr/bin/env python3
"""
19 — Dynamic Quote Token Management

Demonstrates changing a token's quote token. In Tempo, every
TIP-20 USD token has a quoteToken that defines its trading pair
on the DEX. Admins can update this via a two-step process:
  1. setNextQuoteToken(newToken) — stage the change
  2. completeQuoteTokenUpdate() — apply it

Both require DEFAULT_ADMIN_ROLE.
"""
from tempo_utils import *
from eth_abi import decode as abi_decode


def main():
    header("19 · QUOTE TOKEN MANAGEMENT")
    w3, account, chain_id = connect()

    section("1. Create Test Token")
    token = create_token(w3, account, "QuoteTestUSD", "QTUSD")
    if not token:
        fail("Token creation failed")
        return
    kv("Token", token)
    kv("Name", read_string(w3, token, "name"))

    # Check initial quote token
    initial_quote = read_address(w3, token, "quoteToken")
    kv("Initial Quote", "PathUSD" if initial_quote == PATH_USD else initial_quote)

    # ─── Set Supply Cap & Mint ──────────────────────────────
    section("2. Prepare Token")
    # Grant ISSUER_ROLE (required for mint/supply cap on new tokens)
    calldata = encode_grant_role(ISSUER_ROLE, account.address)
    send_tempo_tx(w3, account,
        calls=[Call.create(to=token, value=0, data=calldata)],
        gas_limit=500_000)

    calldata = encode_set_supply_cap(100_000_000_000_000)  # 100M cap
    send_tempo_tx(w3, account,
        calls=[Call.create(to=token, value=0, data=calldata)],
        gas_limit=500_000)
    kv("Supply Cap", "100,000,000")

    calldata = encode_mint(account.address, 1_000_000_000)
    send_tempo_tx(w3, account,
        calls=[Call.create(to=token, value=0, data=calldata)],
        gas_limit=2_000_000)
    kv("Minted", "1,000")

    # ─── Stage Quote Token Change ───────────────────────────
    section("3. Stage Quote Token Change")
    # Change quote from PathUSD → AlphaUSD
    new_quote = ALPHA_USD
    kv("Current Quote", "PathUSD")
    kv("New Quote", "AlphaUSD")

    calldata = encode_set_next_quote_token(new_quote)
    tx_hash, receipt, _ = send_tempo_tx(
        w3, account,
        calls=[Call.create(to=token, value=0, data=calldata)],
        gas_limit=500_000)
    tx_summary(tx_hash, receipt)

    # Verify staged
    raw = call_view(w3, token,
                    selector("nextQuoteToken()"))
    (staged,) = abi_decode(["address"], raw)
    staged = Web3.to_checksum_address(staged)
    kv("Staged Quote", "AlphaUSD" if staged == ALPHA_USD else staged)
    success("Next quote token staged")

    # ─── Complete Update ────────────────────────────────────
    section("4. Complete Quote Token Update")
    calldata = encode_complete_quote_token_update()
    tx_hash, receipt, _ = send_tempo_tx(
        w3, account,
        calls=[Call.create(to=token, value=0, data=calldata)],
        gas_limit=500_000)
    tx_summary(tx_hash, receipt)

    # Verify change
    new_qt = read_address(w3, token, "quoteToken")
    kv("Quote Token Now", "AlphaUSD" if new_qt == ALPHA_USD else new_qt)
    if new_qt == ALPHA_USD:
        success("Quote token updated: PathUSD → AlphaUSD")

    # ─── Verify Supply Cap ──────────────────────────────────
    section("5. Verify Supply Cap")
    cap = read_uint256(w3, token, "supplyCap")
    kv("Supply Cap", fmt_amount(cap))
    total = read_uint256(w3, token, "totalSupply")
    kv("Total Supply", fmt_amount(total))
    kv("Headroom", fmt_amount(cap - total))
    success("Supply cap and quote token management complete")


if __name__ == "__main__":
    main()

