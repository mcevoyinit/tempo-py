#!/usr/bin/env python3
"""
11 — TIP-403 Policy Registry (Transfer Policies)

Demonstrates Tempo's on-chain compliance framework. Transfer policies
control which addresses can send/receive tokens:

  WHITELIST (0): Only authorized addresses can transfer
  BLACKLIST (1): All except blacklisted addresses can transfer
  COMPOUND (2): Separate sender/recipient/mint policies

Registry: 0x403C000000000000000000000000000000000000
"""
from tempo_utils import *


def main():
    header("11 · TIP-403 POLICY REGISTRY")
    w3, account, chain_id = connect()

    section("Setup")
    kv("Registry", TIP403_REGISTRY)
    kv("Admin", account.address[:24] + "...")

    # Check current policy counter
    try:
        raw = call_view(w3, TIP403_REGISTRY, encode_policy_id_counter())
        if raw:
            (counter,) = abi_decode(["uint64"], raw)
            kv("Current Policy Counter", counter)
    except Exception as e:
        kv("Policy Counter", f"query failed: {e}")

    # ─── Create Whitelist Policy ────────────────────────────────
    section("1. Create Whitelist Policy")
    print("  Only whitelisted addresses can transfer")

    calldata = encode_create_policy(account.address, 0)  # WHITELIST = 0
    try:
        tx_hash, receipt, _ = send_tempo_tx(
            w3, account,
            calls=[Call.create(to=TIP403_REGISTRY, value=0, data=calldata)],
        )
        tx_summary(tx_hash, receipt)

        # Extract policy ID from PolicyCreated event
        policy_id = None
        for log in receipt.get("logs", []):
            topics = log.get("topics", [])
            if len(topics) >= 2:
                # PolicyCreated(uint64 indexed policyId, address indexed updater, PolicyType policyType)
                try:
                    policy_id = int(topics[1].hex(), 16)
                    break
                except (ValueError, IndexError):
                    pass

        if policy_id is not None:
            kv("Policy ID", policy_id)
            success(f"Whitelist policy #{policy_id} created")
        else:
            fail("Could not extract policy ID from receipt")
            # Try reading counter to infer
            raw = call_view(w3, TIP403_REGISTRY, encode_policy_id_counter())
            if raw:
                (counter,) = abi_decode(["uint64"], raw)
                policy_id = counter - 1  # Latest created
                kv("Inferred Policy ID", policy_id)

    except Exception as e:
        fail(f"Create policy failed: {e}")
        return

    if policy_id is None:
        fail("No policy ID available")
        return

    # ─── Add Addresses to Whitelist ─────────────────────────────
    section("2. Whitelist Addresses")
    alice = w3.eth.account.create().address
    bob = w3.eth.account.create().address
    charlie = w3.eth.account.create().address  # Not whitelisted

    kv("Alice (whitelisted)", alice[:24] + "...")
    kv("Bob (whitelisted)", bob[:24] + "...")
    kv("Charlie (NOT listed)", charlie[:24] + "...")

    calls = [
        Call.create(to=TIP403_REGISTRY, value=0,
                    data=encode_modify_whitelist(policy_id, alice, True)),
        Call.create(to=TIP403_REGISTRY, value=0,
                    data=encode_modify_whitelist(policy_id, bob, True)),
    ]
    try:
        tx_hash, receipt, _ = send_tempo_tx(w3, account, calls=calls)
        tx_summary(tx_hash, receipt)
        success("Alice and Bob whitelisted in 1 batch tx")
    except Exception as e:
        fail(f"Whitelist update failed: {e}")

    # ─── Check Authorization ────────────────────────────────────
    section("3. Check Authorization")
    for name, addr in [("Alice", alice), ("Bob", bob), ("Charlie", charlie)]:
        try:
            raw = call_view(w3, TIP403_REGISTRY,
                            encode_is_authorized(policy_id, addr))
            if raw:
                (authorized,) = abi_decode(["bool"], raw)
                status = "✓" if authorized else "✗"
                print(f"  {status} {name}: authorized={authorized}")
            else:
                print(f"  ? {name}: no data returned")
        except Exception as e:
            print(f"  ? {name}: query failed: {e}")

    # ─── Remove from Whitelist ──────────────────────────────────
    section("4. Remove Bob from Whitelist")
    try:
        calldata = encode_modify_whitelist(policy_id, bob, False)
        tx_hash, receipt, _ = send_tempo_tx(
            w3, account,
            calls=[Call.create(to=TIP403_REGISTRY, value=0, data=calldata)],
        )
        tx_summary(tx_hash, receipt)

        raw = call_view(w3, TIP403_REGISTRY,
                        encode_is_authorized(policy_id, bob))
        if raw:
            (authorized,) = abi_decode(["bool"], raw)
            if not authorized:
                success("Bob removed from whitelist")
            else:
                fail("Bob still authorized after removal")
    except Exception as e:
        fail(f"Whitelist removal failed: {e}")

    success("Policy registry demonstration complete")


if __name__ == "__main__":
    main()
