#!/usr/bin/env python3
"""
16 — EIP-2612 Permit (Gasless Approvals)

Demonstrates off-chain signed approvals via EIP-2612 permit.
The owner signs a typed-data message off-chain, and anyone
can submit it on-chain to set the allowance.

EIP-712 domain: name=<token name>, version="1", chainId, verifyingContract

NOTE: permit/nonces/DOMAIN_SEPARATOR are T2-gated on TIP-20.
If the node hasn't activated T2 for TIP-20, this script
detects the situation and exits gracefully.
"""
from tempo_utils import *
from eth_abi import decode as abi_decode


def main():
    header("16 · EIP-2612 PERMIT (GASLESS APPROVALS)")
    w3, account, chain_id = connect()

    section("1. Token Info")
    token = PATH_USD
    token_name = read_string(w3, token, "name")
    kv("Token", token_name)
    kv("Address", token)

    # Check if T2 permit functions are available
    try:
        raw = call_view(w3, token, encode_domain_separator())
        (domain_sep,) = abi_decode(["bytes32"], raw)
        kv("DOMAIN_SEPARATOR", "0x" + domain_sep.hex()[:16] + "...")
    except Exception:
        kv("DOMAIN_SEPARATOR", "NOT AVAILABLE")
        kv("Reason", "TIP-20 T2 hardfork not active for permit functions")
        kv("Note", "permit/nonces/DOMAIN_SEPARATOR are T2-gated")
        success("Script complete (T2 permit functions not yet available)")
        return

    # Get current nonce for owner
    raw = call_view(w3, token, encode_nonces(account.address))
    (nonce,) = abi_decode(["uint256"], raw)
    kv("Current Nonce", nonce)

    # ─── Construct EIP-712 Permit ───────────────────────────
    section("2. Sign Permit Off-Chain")
    spender = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"  # Dev2
    value = 500_000_000  # 500 tokens
    deadline = 2**256 - 1  # Never expires

    # PERMIT_TYPEHASH
    permit_typehash = Web3.keccak(
        text="Permit(address owner,address spender,uint256 value,"
             "uint256 nonce,uint256 deadline)")

    # Struct hash
    struct_hash = Web3.keccak(
        abi_encode(
            ["bytes32", "address", "address", "uint256", "uint256", "uint256"],
            [permit_typehash, account.address, spender, value, nonce, deadline]))

    # EIP-712 digest
    digest = Web3.keccak(
        b"\x19\x01" + domain_sep + struct_hash)

    kv("Spender", spender[:10] + "...")
    kv("Value", fmt_amount(value))
    kv("Deadline", "MAX (never expires)")
    kv("Digest", "0x" + digest.hex()[:16] + "...")

    # Sign the digest
    from eth_keys import keys
    pk = keys.PrivateKey(bytes.fromhex(DEV_PRIVATE_KEY[2:]))
    sig = pk.sign_msg_hash(digest)
    v = sig.v + 27
    r = sig.r.to_bytes(32, "big")
    s = sig.s.to_bytes(32, "big")

    kv("v", v)
    kv("r", "0x" + r.hex()[:16] + "...")
    kv("s", "0x" + s.hex()[:16] + "...")
    success("Permit signed off-chain (no gas spent)")

    # ─── Submit Permit On-Chain ─────────────────────────────
    section("3. Submit Permit On-Chain")

    # Check allowance before
    raw = call_view(w3, token,
                    encode_allowance(account.address, spender))
    (before,) = abi_decode(["uint256"], raw)
    kv("Allowance Before", fmt_amount(before))

    # Call permit
    calldata = encode_permit(account.address, spender, value, deadline,
                              v, r, s)
    tx_hash, receipt, _ = send_tempo_tx(
        w3, account,
        calls=[Call.create(to=token, value=0, data=calldata)],
        gas_limit=500_000,
    )
    tx_summary(tx_hash, receipt)

    # Check allowance after
    raw = call_view(w3, token,
                    encode_allowance(account.address, spender))
    (after,) = abi_decode(["uint256"], raw)
    kv("Allowance After", fmt_amount(after))

    if after == value:
        success(f"Permit set allowance to {fmt_amount(value)} without "
                f"spender needing a transaction")

    # Verify nonce incremented
    section("4. Verify Nonce Increment")
    raw = call_view(w3, token, encode_nonces(account.address))
    (new_nonce,) = abi_decode(["uint256"], raw)
    kv("Nonce Before", nonce)
    kv("Nonce After", new_nonce)
    if new_nonce == nonce + 1:
        success("Nonce incremented (replay protection active)")

    success("EIP-2612 permit demonstration complete")


if __name__ == "__main__":
    main()
