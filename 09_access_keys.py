#!/usr/bin/env python3
"""
09 — Access Keys (Account Keychain)

Demonstrates Tempo's protocol-level access key system. Unlike Ethereum
where all txs need the main private key, Tempo lets you authorize secondary
keys with:
  - Expiry timestamps
  - Per-token spending limits
  - Signature type flexibility (secp256k1, P256, WebAuthn)

Keychain Precompile: 0xaAAAaaAA00000000000000000000000000000000
"""
import time

import sys
sys.path.insert(0, "/Users/mcevoyinit/eric/pytempo")

from tempo_utils import *
from pytempo import TempoTransaction, Call, KeyAuthorization, TokenLimit, sign_tx_access_key


def main():
    header("09 · ACCESS KEYS (KEYCHAIN)")
    w3, account, chain_id = connect()

    section("Setup")
    kv("Root Account", account.address[:24] + "...")
    kv("Keychain", ACCOUNT_KEYCHAIN)

    # Create an access key (a separate keypair)
    access_key_acct = w3.eth.account.create()
    access_key_addr = access_key_acct.address
    access_key_pk = "0x" + access_key_acct.key.hex()

    expiry = int(time.time()) + 3600  # 1 hour from now
    spending_limit = 5_000_000  # 5 PathUSD

    kv("Access Key", access_key_addr[:24] + "...")
    kv("Expiry", f"{expiry} (1 hour)")
    kv("Spending Limit", f"{fmt_amount(spending_limit)} PathUSD")

    # ─── Authorize Access Key ───────────────────────────────────
    section("1. Authorize Access Key")

    calldata = encode_authorize_key(
        key_id=access_key_addr,
        sig_type=0,  # Secp256k1
        expiry=expiry,
        enforce_limits=True,
        limits=[(PATH_USD, spending_limit)],
    )

    try:
        tx_hash, receipt, _ = send_tempo_tx(
            w3, account,
            calls=[Call.create(to=ACCOUNT_KEYCHAIN, value=0, data=calldata)],
        )
        tx_summary(tx_hash, receipt)

        if receipt["status"] == 1:
            success("Access key authorized on-chain")
        else:
            fail("Authorization failed")
            return
    except Exception as e:
        fail(f"Authorization tx failed: {e}")
        print("  Note: Keychain may not be available in dev mode")
        return

    # ─── Query Access Key Info ──────────────────────────────────
    section("2. Query Access Key")
    try:
        key_data = call_view(w3, ACCOUNT_KEYCHAIN,
                             encode_get_key(account.address, access_key_addr))
        if key_data:
            # KeyInfo: (uint8 sigType, address keyId, uint64 expiry, bool enforceLimits, bool isRevoked)
            decoded = abi_decode(
                ["(uint8,address,uint64,bool,bool)"], key_data
            )
            info = decoded[0]
            kv("Sig Type", ["Secp256k1", "P256", "WebAuthn"][info[0]])
            kv("Key ID", info[1][:24] + "...")
            kv("Expiry", info[2])
            kv("Enforce Limits", info[3])
            kv("Is Revoked", info[4])
        else:
            print("  No key data returned")
    except Exception as e:
        print(f"  Query error: {e}")

    # ─── Use Access Key to Sign Transaction ─────────────────────
    section("3. Sign Transaction with Access Key")
    recipient = w3.eth.account.create().address
    send_amount = 1_000_000  # 1 PathUSD

    kv("Recipient", recipient[:24] + "...")
    kv("Amount", f"{fmt_amount(send_amount)} PathUSD")

    transfer_data = encode_transfer(recipient, send_amount)
    gas_price = w3.eth.gas_price or 20_000_000_000
    nonce = w3.eth.get_transaction_count(account.address)

    # Key already authorized via precompile in step 1
    # Just sign the tx with the access key (no inline key_authorization needed)
    import time as _time
    _time.sleep(2)  # Wait for authorization tx to be confirmed
    nonce = w3.eth.get_transaction_count(account.address)

    tx = TempoTransaction.create(
        chain_id=chain_id,
        gas_limit=1_000_000,
        max_fee_per_gas=gas_price * 3,
        max_priority_fee_per_gas=gas_price,
        nonce=nonce,
        fee_token=PATH_USD,
        calls=(Call.create(to=PATH_USD, value=0, data=transfer_data),),
    )

    # Sign with the access key (not root key)
    signed_tx = sign_tx_access_key(tx, access_key_pk, account.address)
    print("  Signed with access key (not root key)")

    try:
        tx_hash = w3.eth.send_raw_transaction(signed_tx.encode())
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
        tx_summary(tx_hash, receipt)

        bal = get_balance(w3, PATH_USD, recipient)
        if bal == send_amount:
            success(f"Access key transferred {fmt_amount(send_amount)} PathUSD")
        else:
            fail(f"Balance mismatch: {fmt_amount(bal)}")
    except Exception as e:
        fail(f"Access key tx failed: {e}")
        print("  Note: Access key transactions may require key_authorization")

    # ─── Check Remaining Limit ──────────────────────────────────
    section("4. Check Remaining Spending Limit")
    try:
        limit_data = call_view(
            w3, ACCOUNT_KEYCHAIN,
            encode_get_remaining_limit(account.address, access_key_addr, PATH_USD),
        )
        if limit_data:
            (remaining,) = abi_decode(["uint256"], limit_data)
            kv("Remaining Limit", fmt_amount(remaining))
            kv("Spent", fmt_amount(spending_limit - remaining))
        else:
            print("  No limit data returned")
    except Exception as e:
        print(f"  Limit query error: {e}")

    # ─── Revoke Access Key ──────────────────────────────────────
    section("5. Revoke Access Key")
    _time.sleep(2)
    try:
        calldata = encode_revoke_key(access_key_addr)
        tx_hash, receipt, _ = send_tempo_tx(
            w3, account,
            calls=[Call.create(to=ACCOUNT_KEYCHAIN, value=0, data=calldata)],
        )
        tx_summary(tx_hash, receipt)
        if receipt["status"] == 1:
            success("Access key revoked — can no longer sign transactions")
        else:
            fail("Revocation failed")
    except Exception as e:
        fail(f"Revocation failed: {e}")

    success("Access key lifecycle complete")


if __name__ == "__main__":
    main()
