#!/usr/bin/env python3
"""
20 — TIP-403 Compound Policies (TIP-1015)

Demonstrates directional transfer policies using compound policies.
A compound policy combines three sub-policies for independent
sender, recipient, and mint-recipient authorization.

This allows rules like: "anyone can send, but only whitelisted
addresses can receive" — directional authorization.
"""
from tempo_utils import *
from eth_abi import decode as abi_decode


def main():
    header("20 · COMPOUND POLICIES (TIP-1015)")
    w3, account, chain_id = connect()

    section("1. Create Sub-Policies")
    # Policy 1: Whitelist for senders
    raw = call_view(w3, TIP403_REGISTRY, encode_policy_id_counter())
    (next_id,) = abi_decode(["uint64"], raw)

    # Create whitelist policy (type 0 = WHITELIST)
    calldata = encode_create_policy(account.address, 0)
    tx_hash, receipt, _ = send_tempo_tx(
        w3, account,
        calls=[Call.create(to=TIP403_REGISTRY, value=0, data=calldata)],
        gas_limit=500_000)
    sender_policy_id = next_id
    kv("Sender Policy", f"#{sender_policy_id} (WHITELIST)")
    tx_summary(tx_hash, receipt)

    # Create blacklist policy (type 1 = BLACKLIST)
    calldata = encode_create_policy(account.address, 1)
    tx_hash, receipt, _ = send_tempo_tx(
        w3, account,
        calls=[Call.create(to=TIP403_REGISTRY, value=0, data=calldata)],
        gas_limit=500_000)
    recipient_policy_id = sender_policy_id + 1
    kv("Recipient Policy", f"#{recipient_policy_id} (BLACKLIST)")

    # Use policy 1 (always allow) for mint recipients
    mint_policy_id = 1
    kv("Mint Recipient", f"#{mint_policy_id} (ALWAYS ALLOW)")
    success("Three sub-policies ready")

    # ─── Populate Sub-Policies ──────────────────────────────
    section("2. Configure Sub-Policies")
    # Whitelist: allow dev1 as sender
    calldata = encode_modify_whitelist(sender_policy_id,
                                        account.address, True)
    send_tempo_tx(w3, account,
        calls=[Call.create(to=TIP403_REGISTRY, value=0, data=calldata)],
        gas_limit=500_000)
    kv("Sender WL", f"Added {account.address[:10]}...")

    # Whitelist: allow dev2 as sender
    dev2 = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
    calldata = encode_modify_whitelist(sender_policy_id, dev2, True)
    send_tempo_tx(w3, account,
        calls=[Call.create(to=TIP403_REGISTRY, value=0, data=calldata)],
        gas_limit=500_000)
    kv("Sender WL", f"Added {dev2[:10]}...")

    # Blacklist: restrict a specific address as recipient
    restricted = "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"  # dev3
    calldata = encode_modify_blacklist(recipient_policy_id,
                                        restricted, True)
    send_tempo_tx(w3, account,
        calls=[Call.create(to=TIP403_REGISTRY, value=0, data=calldata)],
        gas_limit=500_000)
    kv("Recipient BL", f"Blocked {restricted[:10]}...")
    success("Sub-policies configured")

    # ─── Create Compound Policy ─────────────────────────────
    section("3. Create Compound Policy")
    calldata = encode_create_compound_policy(
        sender_policy_id, recipient_policy_id, mint_policy_id)
    tx_hash, receipt, _ = send_tempo_tx(
        w3, account,
        calls=[Call.create(to=TIP403_REGISTRY, value=0, data=calldata)],
        gas_limit=2_000_000)
    tx_summary(tx_hash, receipt)

    raw = call_view(w3, TIP403_REGISTRY, encode_policy_id_counter())
    (compound_id,) = abi_decode(["uint64"], raw)
    compound_id -= 1  # Last created
    kv("Compound ID", compound_id)

    # Verify compound data
    raw = call_view(w3, TIP403_REGISTRY,
                    encode_compound_policy_data(compound_id))
    (s_id, r_id, m_id) = abi_decode(["uint64", "uint64", "uint64"], raw)
    kv("Sender Sub", f"#{s_id} (WHITELIST)")
    kv("Recipient Sub", f"#{r_id} (BLACKLIST)")
    kv("Mint Sub", f"#{m_id} (ALWAYS ALLOW)")
    success("Compound policy created")

    # ─── Test Directional Authorization ─────────────────────
    section("4. Directional Authorization Tests")

    # Test sender authorization
    raw = call_view(w3, TIP403_REGISTRY,
                    encode_is_authorized_sender(compound_id, account.address))
    (auth,) = abi_decode(["bool"], raw)
    kv(f"Dev1 as Sender", f"{'ALLOWED' if auth else 'DENIED'}")

    raw = call_view(w3, TIP403_REGISTRY,
                    encode_is_authorized_sender(compound_id, restricted))
    (auth,) = abi_decode(["bool"], raw)
    kv(f"Dev3 as Sender", f"{'ALLOWED' if auth else 'DENIED'} (not whitelisted)")

    # Test recipient authorization
    raw = call_view(w3, TIP403_REGISTRY,
                    encode_is_authorized_recipient(compound_id, dev2))
    (auth,) = abi_decode(["bool"], raw)
    kv(f"Dev2 as Recipient", f"{'ALLOWED' if auth else 'DENIED'}")

    raw = call_view(w3, TIP403_REGISTRY,
                    encode_is_authorized_recipient(compound_id, restricted))
    (auth,) = abi_decode(["bool"], raw)
    kv(f"Dev3 as Recipient", f"{'ALLOWED' if auth else 'DENIED'} (blacklisted)")

    # Test mint recipient authorization
    raw = call_view(w3, TIP403_REGISTRY,
                    encode_is_authorized_mint_recipient(compound_id, restricted))
    (auth,) = abi_decode(["bool"], raw)
    kv(f"Dev3 as MintRecip", f"{'ALLOWED' if auth else 'DENIED'} (always allow)")

    success("Directional authorization verified")

    # ─── Summary ────────────────────────────────────────────
    section("5. Policy Summary")
    kv("Compound", f"Policy #{compound_id}")
    kv("Senders", "Whitelist: Dev1, Dev2 allowed; others denied")
    kv("Recipients", "Blacklist: Dev3 blocked; others allowed")
    kv("Mint Recip", "All allowed (policy #1)")
    success("Compound policy (TIP-1015) demonstration complete")


if __name__ == "__main__":
    main()
