#!/usr/bin/env python3
"""
17 — Burn Blocked (Policy-Enforced Burning)

Demonstrates the burnBlocked function, which burns tokens held
by addresses BLOCKED by the token's transfer policy. This is an
enforcement mechanism: when an address is blacklisted, an authorized
burner can remove their tokens.

Flow:
  1. Create a blacklist policy
  2. Block a target address
  3. Set the policy on the token
  4. burnBlocked removes tokens from the blocked address
"""
from tempo_utils import *
from eth_abi import decode as abi_decode


def main():
    header("17 · BURN BLOCKED (POLICY ENFORCEMENT)")
    w3, account, chain_id = connect()

    section("1. Create Test Token")
    token = create_token(w3, account, "BurnTestUSD", "BTUSD")
    if not token:
        fail("Token creation failed")
        return
    kv("Token", read_string(w3, token, "name"))
    kv("Address", token)

    # Grant ISSUER_ROLE (required for mint/supply cap on new tokens)
    calldata = encode_grant_role(ISSUER_ROLE, account.address)
    send_tempo_tx(w3, account,
        calls=[Call.create(to=token, value=0, data=calldata)],
        gas_limit=500_000)

    # Set supply cap and mint
    calldata = encode_set_supply_cap(100_000_000_000_000)
    send_tempo_tx(w3, account,
        calls=[Call.create(to=token, value=0, data=calldata)],
        gas_limit=500_000)

    target = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"  # Dev2
    mint_amount = 1_000_000_000  # 1000 tokens
    calldata = encode_mint(target, mint_amount)
    send_tempo_tx(w3, account,
        calls=[Call.create(to=token, value=0, data=calldata)],
        gas_limit=2_000_000)
    kv("Minted", f"{fmt_amount(mint_amount)} to {target[:10]}...")
    kv("Target Balance", fmt_amount(get_balance(w3, token, target)))

    # ─── Create Blacklist Policy ────────────────────────────
    section("2. Create Blacklist & Block Target")
    raw = call_view(w3, TIP403_REGISTRY, encode_policy_id_counter())
    (policy_id,) = abi_decode(["uint64"], raw)

    # Create blacklist policy (type 1)
    calldata = encode_create_policy(account.address, 1)
    send_tempo_tx(w3, account,
        calls=[Call.create(to=TIP403_REGISTRY, value=0, data=calldata)],
        gas_limit=500_000)
    kv("Policy ID", f"#{policy_id} (BLACKLIST)")

    # Block the target address
    calldata = encode_modify_blacklist(policy_id, target, True)
    send_tempo_tx(w3, account,
        calls=[Call.create(to=TIP403_REGISTRY, value=0, data=calldata)],
        gas_limit=500_000)
    kv("Blocked", f"{target[:10]}...")

    # Verify blocked
    raw = call_view(w3, TIP403_REGISTRY,
                    encode_is_authorized(policy_id, target))
    (auth,) = abi_decode(["bool"], raw)
    kv("Is Authorized", f"{auth} (should be False)")
    if not auth:
        success("Target is blocked by blacklist policy")

    # Verify admin is NOT blocked
    raw = call_view(w3, TIP403_REGISTRY,
                    encode_is_authorized(policy_id, account.address))
    (auth,) = abi_decode(["bool"], raw)
    kv("Admin Authorized", auth)

    # ─── Set Policy on Token ────────────────────────────────
    section("3. Apply Policy to Token")
    calldata = encode_change_transfer_policy_id(policy_id)
    tx_hash, receipt, _ = send_tempo_tx(
        w3, account,
        calls=[Call.create(to=token, value=0, data=calldata)],
        gas_limit=500_000)
    tx_summary(tx_hash, receipt)

    # Verify policy set
    raw = call_view(w3, token, encode_transfer_policy_id())
    (set_id,) = abi_decode(["uint64"], raw)
    kv("Token Policy", f"#{set_id}")
    success(f"Blacklist policy #{policy_id} applied to token")

    # ─── Grant BURN_BLOCKED_ROLE ────────────────────────────
    section("4. Grant BURN_BLOCKED_ROLE")
    calldata = encode_grant_role(BURN_BLOCKED_ROLE, account.address)
    send_tempo_tx(w3, account,
        calls=[Call.create(to=token, value=0, data=calldata)],
        gas_limit=500_000)

    raw = call_view(w3, token,
                    encode_has_role(BURN_BLOCKED_ROLE, account.address))
    (has,) = abi_decode(["bool"], raw)
    kv("Has BURN_BLOCKED_ROLE", has)
    success("Role granted to admin")

    # ─── Execute Burn Blocked ───────────────────────────────
    section("5. Burn Tokens from Blocked Address")
    before = get_balance(w3, token, target)
    kv("Target Bal Before", fmt_amount(before))

    burn_amount = 500_000_000  # 500 tokens
    calldata = encode_burn_blocked(target, burn_amount)
    tx_hash, receipt, _ = send_tempo_tx(
        w3, account,
        calls=[Call.create(to=token, value=0, data=calldata)],
        gas_limit=1_000_000)
    tx_summary(tx_hash, receipt)

    after = get_balance(w3, token, target)
    burned = before - after
    kv("Target Bal After", fmt_amount(after))
    kv("Burned", fmt_amount(burned))
    if burned == burn_amount:
        success(f"Burned {fmt_amount(burn_amount)} from blocked address")

    # ─── Verify Supply ──────────────────────────────────────
    section("6. Verify Supply Reduction")
    total = read_uint256(w3, token, "totalSupply")
    kv("Total Supply", fmt_amount(total))
    kv("Expected", fmt_amount(mint_amount - burn_amount))
    if total == mint_amount - burn_amount:
        success("Total supply reduced correctly")

    # Cleanup: restore allow-all policy
    calldata = encode_change_transfer_policy_id(1)
    send_tempo_tx(w3, account,
        calls=[Call.create(to=token, value=0, data=calldata)],
        gas_limit=500_000)
    success("Restored allow-all policy on token")

    success("Burn blocked (policy enforcement) demonstration complete")


if __name__ == "__main__":
    main()
