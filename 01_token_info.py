#!/usr/bin/env python3
"""
01 — TIP-20 Token Info (Read-Only Queries)

Demonstrates reading on-chain token metadata without sending any transactions.
Queries PathUSD (Tempo's default fee token) for all standard TIP-20 properties.
"""
from tempo_utils import *


def main():
    header("01 · TIP-20 TOKEN INFO")
    w3, account, chain_id = connect()

    section("Connection")
    kv("RPC", NODE1_RPC)
    kv("Chain ID", chain_id)
    kv("Block", w3.eth.block_number)

    section("PathUSD Token Properties")
    kv("Address", PATH_USD)
    kv("Name", read_string(w3, PATH_USD, "name"))
    kv("Symbol", read_string(w3, PATH_USD, "symbol"))
    kv("Decimals", read_uint8(w3, PATH_USD, "decimals"))
    kv("Currency", read_string(w3, PATH_USD, "currency"))

    total = read_uint256(w3, PATH_USD, "totalSupply")
    kv("Total Supply", fmt_amount(total))
    kv("Paused", read_bool(w3, PATH_USD, "paused"))

    section("Account Balances")
    dev_bal = get_balance(w3, PATH_USD, account.address)
    kv("Dev Account", fmt_amount(dev_bal))

    # Check a zero-balance account
    random_addr = w3.eth.account.create().address
    zero_bal = get_balance(w3, PATH_USD, random_addr)
    kv("Random Account", fmt_amount(zero_bal))

    section("Role Checks (Dev Account)")
    for role_name, role_hash in [
        ("DEFAULT_ADMIN", DEFAULT_ADMIN_ROLE),
        ("ISSUER", ISSUER_ROLE),
        ("PAUSE", PAUSE_ROLE),
    ]:
        data = encode_has_role(role_hash, account.address)
        raw = call_view(w3, PATH_USD, data)
        has = abi_decode(["bool"], raw)[0] if raw else False
        kv(f"Has {role_name}", has)

    success("Token info queries complete")


if __name__ == "__main__":
    main()
