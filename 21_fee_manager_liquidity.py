#!/usr/bin/env python3
"""
21 — Fee Manager: AMM Liquidity Management

Demonstrates advanced Fee Manager operations: querying pool
state, checking LP balances, and removing liquidity (burn).
Builds on script 12's liquidity addition.

Pool struct returns (uint128 reserveUserToken, uint128 reserveValidatorToken).
Total supply is queried separately via totalSupply(bytes32).
"""
from tempo_utils import *
from eth_abi import decode as abi_decode


def query_pool(w3, user_token, validator_token):
    """Query pool reserves and total supply."""
    raw = call_view(w3, TIP_FEE_MANAGER,
                    encode_get_pool(user_token, validator_token))
    (reserve_user, reserve_validator) = abi_decode(
        ["uint128", "uint128"], raw)

    raw = call_view(w3, TIP_FEE_MANAGER,
                    encode_get_pool_id(user_token, validator_token))
    (pool_id,) = abi_decode(["bytes32"], raw)

    raw = call_view(w3, TIP_FEE_MANAGER,
                    encode_pool_total_supply(pool_id))
    (total_supply,) = abi_decode(["uint256"], raw)

    return reserve_user, reserve_validator, total_supply, pool_id


def main():
    header("21 · FEE MANAGER (LIQUIDITY MANAGEMENT)")
    w3, account, chain_id = connect()

    section("1. Setup")
    user_token = ALPHA_USD
    validator_token = PATH_USD
    kv("User Token", read_string(w3, user_token, "name"))
    kv("Validator Token", read_string(w3, validator_token, "name"))

    # ─── Query Pool State ───────────────────────────────────
    section("2. Query Pool State")
    res_u, res_v, lp_supply, pool_id = query_pool(
        w3, user_token, validator_token)
    kv("Reserve User", fmt_amount(res_u))
    kv("Reserve Validator", fmt_amount(res_v))
    kv("LP Supply", fmt_amount(lp_supply))
    kv("Pool ID", "0x" + pool_id.hex()[:16] + "...")

    needs_liquidity = lp_supply == 0

    # ─── Add Liquidity (if pool is empty) ───────────────────
    if needs_liquidity:
        section("3. Add Initial Liquidity")
        add_amount = 1_000_000_000  # 1000 tokens
        calldata = encode_add_liquidity(
            user_token, validator_token, add_amount, account.address)
        tx_hash, receipt, _ = send_tempo_tx(
            w3, account,
            calls=[Call.create(to=TIP_FEE_MANAGER, value=0, data=calldata)],
            gas_limit=5_000_000,
        )
        kv("Added", fmt_amount(add_amount))
        tx_summary(tx_hash, receipt)

        # Re-query pool
        res_u, res_v, lp_supply, pool_id = query_pool(
            w3, user_token, validator_token)
        kv("Reserve User", fmt_amount(res_u))
        kv("Reserve Validator", fmt_amount(res_v))
        kv("LP Supply", fmt_amount(lp_supply))
    else:
        section("3. Pool Already Has Liquidity")
        success("Skipping add — pool has existing reserves")

    # ─── Query LP Balance ──────────────────────────────────
    section("4. LP Balance")
    raw = call_view(w3, TIP_FEE_MANAGER,
                    encode_liquidity_balances(pool_id, account.address))
    (lp_bal,) = abi_decode(["uint256"], raw)
    kv("My LP Balance", fmt_amount(lp_bal))
    kv("Total LP Supply", fmt_amount(lp_supply))

    if lp_supply > 0:
        share = (lp_bal / lp_supply) * 100
        kv("My Pool Share", f"{share:.2f}%")
    success("Pool introspection complete")

    # ─── Remove Liquidity ───────────────────────────────────
    if lp_bal > 0:
        section("5. Remove Liquidity (Burn LP)")
        burn_amount = lp_bal // 4  # Remove 25% of our LP

        alpha_before = get_balance(w3, user_token, account.address)
        pusd_before = get_balance(w3, validator_token, account.address)

        calldata = encode_burn_liquidity(
            user_token, validator_token, burn_amount, account.address)
        tx_hash, receipt, _ = send_tempo_tx(
            w3, account,
            calls=[Call.create(to=TIP_FEE_MANAGER, value=0, data=calldata)],
            gas_limit=5_000_000,
        )
        tx_summary(tx_hash, receipt)

        alpha_after = get_balance(w3, user_token, account.address)
        pusd_after = get_balance(w3, validator_token, account.address)

        kv("LP Burned", fmt_amount(burn_amount))
        kv("AlphaUSD Got", fmt_amount(alpha_after - alpha_before))
        kv("PathUSD Got", fmt_amount(pusd_after - pusd_before))

        # Verify pool state after
        section("6. Pool State After Burn")
        res_u, res_v, lp_supply, _ = query_pool(
            w3, user_token, validator_token)
        kv("Reserve User", fmt_amount(res_u))
        kv("Reserve Validator", fmt_amount(res_v))
        kv("LP Supply", fmt_amount(lp_supply))

        raw = call_view(w3, TIP_FEE_MANAGER,
                        encode_liquidity_balances(pool_id, account.address))
        (new_lp,) = abi_decode(["uint256"], raw)
        kv("My LP Remaining", fmt_amount(new_lp))
        if new_lp < lp_bal:
            success(f"Successfully removed {fmt_amount(burn_amount)} LP tokens")
    else:
        section("5. Skip Burn")
        kv("Note", "No LP tokens to burn")

    success("Fee Manager liquidity management demonstration complete")


if __name__ == "__main__":
    main()
