#!/usr/bin/env python3
"""
05 — TIP-20 Token Creation

Demonstrates creating a new TIP-20 stablecoin token via the TIP-20 Factory
precompile. Tokens are deployed deterministically from sender + salt.

Factory: 0x20FC000000000000000000000000000000000000
Function: createToken(string name, string symbol, string currency,
                      address quoteToken, address admin, bytes32 salt)
"""
import os
from tempo_utils import *


def main():
    header("05 · TIP-20 TOKEN CREATION")
    w3, account, chain_id = connect()

    section("Setup")
    kv("Factory", TIP20_FACTORY)
    kv("Admin", account.address)
    kv("Quote Token", f"PathUSD ({PATH_USD[:18]}...)")

    # Deterministic salt for reproducible address
    salt = Web3.keccak(text="demo-token-v1-" + str(os.getpid()))
    token_name = "DemoUSD"
    token_symbol = "DUSD"
    token_currency = "USD"

    kv("Token Name", token_name)
    kv("Token Symbol", token_symbol)
    kv("Currency", token_currency)
    kv("Salt", salt.hex()[:20] + "...")

    section("Creating Token")
    calldata = encode_create_token(
        token_name, token_symbol, token_currency,
        PATH_USD, account.address, salt,
    )
    tx_hash, receipt, _ = send_tempo_tx(
        w3, account,
        calls=[Call.create(to=TIP20_FACTORY, value=0, data=calldata)],
        gas_limit=3_000_000,
    )
    tx_summary(tx_hash, receipt)

    # Extract token address from TokenCreated event (topic[1])
    new_token = None
    for log in receipt.get("logs", []):
        topics = log.get("topics", [])
        if len(topics) >= 2:
            # TokenCreated event: token address is indexed as topic[1]
            addr_hex = "0x" + topics[1].hex()[-40:]
            candidate = Web3.to_checksum_address(addr_hex)
            # Verify it has TIP-20 prefix (0x20C0...)
            if candidate.lower().startswith("0x20c0"):
                new_token = candidate
                break

    if new_token:
        section("New Token Info")
        kv("Address", new_token)
        kv("Name", read_string(w3, new_token, "name"))
        kv("Symbol", read_string(w3, new_token, "symbol"))
        kv("Decimals", read_uint8(w3, new_token, "decimals"))
        kv("Currency", read_string(w3, new_token, "currency"))
        kv("Total Supply", fmt_amount(read_uint256(w3, new_token, "totalSupply")))
        kv("Paused", read_bool(w3, new_token, "paused"))

        # Verify admin role
        data = encode_has_role(DEFAULT_ADMIN_ROLE, account.address)
        raw = call_view(w3, new_token, data)
        is_admin = abi_decode(["bool"], raw)[0] if raw else False
        kv("Creator is Admin", is_admin)

        success(f"Token {token_symbol} created at {new_token}")
        print(f"\n  Token address for other scripts: {new_token}")
    else:
        fail("Could not extract new token address from receipt")
        print("  Logs:")
        for i, log in enumerate(receipt.get("logs", [])):
            topics = log.get("topics", [])
            print(f"    Log {i}: {len(topics)} topics")
            for j, t in enumerate(topics):
                print(f"      topic[{j}]: {t.hex()}")


if __name__ == "__main__":
    main()
