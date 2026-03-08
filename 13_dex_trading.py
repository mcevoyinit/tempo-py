#!/usr/bin/env python3
"""
13 — Stablecoin DEX: Limit Orders

Demonstrates the on-chain central limit order book (CLOB) for
stablecoin trading. Creates a trading pair, places bid and ask
orders, queries the orderbook, and cancels orders.

The DEX operates on TIP-20 USD tokens. AlphaUSD's quoteToken is
PathUSD, forming the AlphaUSD/PathUSD pair.
"""
from tempo_utils import *
from eth_abi import decode as abi_decode


def main():
    header("13 · STABLECOIN DEX (LIMIT ORDERS)")
    w3, account, chain_id = connect()

    section("1. Verify AlphaUSD Token")
    alpha_name = read_string(w3, ALPHA_USD, "name")
    if not alpha_name:
        fail("AlphaUSD not found — genesis may lack extra tokens")
        return
    alpha_quote = read_address(w3, ALPHA_USD, "quoteToken")
    kv("Token", alpha_name)
    kv("Quote Token", "PathUSD" if alpha_quote == PATH_USD else alpha_quote)
    kv("AlphaUSD Bal", fmt_amount(get_balance(w3, ALPHA_USD, account.address)))
    kv("PathUSD Bal", fmt_amount(get_balance(w3, PATH_USD, account.address)))

    # Approve DEX to escrow tokens (required for order placement)
    approve_dex(w3, account)
    success("DEX approved for AlphaUSD + PathUSD")

    # ─── Create Pair ──────────────────────────────────────────
    section("2. Create Trading Pair")
    calldata = encode_create_pair(ALPHA_USD)
    try:
        tx_hash, receipt, _ = send_tempo_tx(
            w3, account,
            calls=[Call.create(to=STABLECOIN_DEX, value=0, data=calldata)],
            gas_limit=2_000_000,
        )
        if receipt["status"] == 1:
            success("AlphaUSD/PathUSD pair created")
        else:
            kv("Pair", "Creation reverted (may already exist)")
    except Exception as e:
        kv("Pair", "Already exists (OK)")

    # Get pair key
    raw = call_view(w3, STABLECOIN_DEX,
                    encode_dex_pair_key(ALPHA_USD, PATH_USD))
    (pair_key,) = abi_decode(["bytes32"], raw)
    kv("Pair Key", "0x" + pair_key.hex()[:16] + "...")

    # ─── Place Bid ────────────────────────────────────────────
    section("3. Place Bid Order (Buy AlphaUSD)")
    order_amount = 200_000_000  # 200 tokens
    bid_tick = 0                # price = 1.0000

    raw = call_view(w3, STABLECOIN_DEX, encode_next_order_id())
    (bid_id,) = abi_decode(["uint128"], raw)

    calldata = encode_place(ALPHA_USD, order_amount, True, bid_tick)
    tx_hash, receipt, _ = send_tempo_tx(
        w3, account,
        calls=[Call.create(to=STABLECOIN_DEX, value=0, data=calldata)],
        gas_limit=5_000_000,
    )
    kv("Order ID", bid_id)
    kv("Side", "BID (buy AlphaUSD with PathUSD)")
    kv("Amount", f"{fmt_amount(order_amount)} AlphaUSD")
    kv("Tick", f"{bid_tick} (price = 1.0000)")
    tx_summary(tx_hash, receipt)

    # ─── Place Ask ────────────────────────────────────────────
    section("4. Place Ask Order (Sell AlphaUSD)")
    ask_tick = 10  # price = 1.0001

    raw = call_view(w3, STABLECOIN_DEX, encode_next_order_id())
    (ask_id,) = abi_decode(["uint128"], raw)

    calldata = encode_place(ALPHA_USD, order_amount, False, ask_tick)
    tx_hash, receipt, _ = send_tempo_tx(
        w3, account,
        calls=[Call.create(to=STABLECOIN_DEX, value=0, data=calldata)],
        gas_limit=5_000_000,
    )
    kv("Order ID", ask_id)
    kv("Side", "ASK (sell AlphaUSD for PathUSD)")
    kv("Amount", f"{fmt_amount(order_amount)} AlphaUSD")
    kv("Tick", f"{ask_tick} (price = 1.0001)")
    tx_summary(tx_hash, receipt)

    # ─── Query Orders ─────────────────────────────────────────
    section("5. Query Live Orders")
    for label, oid in [("Bid", bid_id), ("Ask", ask_id)]:
        raw = call_view(w3, STABLECOIN_DEX, encode_get_order(oid))
        o = abi_decode(
            ["uint128", "address", "bytes32", "bool", "int16",
             "uint128", "uint128", "uint128", "uint128", "bool", "int16"],
            raw)
        side = "BID" if o[3] else "ASK"
        kv(f"{label} #{o[0]}", f"{side} tick={o[4]} "
           f"amount={fmt_amount(o[5])} remaining={fmt_amount(o[6])}")

    # ─── Orderbook State ──────────────────────────────────────
    section("6. Orderbook State")
    raw = call_view(w3, STABLECOIN_DEX, encode_dex_books(pair_key))
    book = abi_decode(["address", "address", "int16", "int16"], raw)
    base_addr = Web3.to_checksum_address(book[0])
    quote_addr = Web3.to_checksum_address(book[1])
    kv("Base", read_string(w3, base_addr, "name"))
    kv("Quote", read_string(w3, quote_addr, "name"))
    kv("Best Bid Tick", book[2])
    kv("Best Ask Tick", book[3])
    spread = book[3] - book[2]
    kv("Spread", f"{spread} ticks ({spread / 100_000:.4%})")

    # ─── Cancel Ask ───────────────────────────────────────────
    section("7. Cancel Ask Order")
    alpha_before = get_balance(w3, ALPHA_USD, account.address)

    calldata = encode_cancel_order(ask_id)
    tx_hash, receipt, _ = send_tempo_tx(
        w3, account,
        calls=[Call.create(to=STABLECOIN_DEX, value=0, data=calldata)],
        gas_limit=5_000_000,
    )
    kv("Cancelled", f"Ask #{ask_id}")
    tx_summary(tx_hash, receipt)

    alpha_after = get_balance(w3, ALPHA_USD, account.address)
    refund = alpha_after - alpha_before
    kv("AlphaUSD Refund", fmt_amount(refund))
    success(f"Escrowed AlphaUSD returned to maker")

    # Verify bid still active
    raw = call_view(w3, STABLECOIN_DEX, encode_get_order(bid_id))
    o = abi_decode(
        ["uint128", "address", "bytes32", "bool", "int16",
         "uint128", "uint128", "uint128", "uint128", "bool", "int16"],
        raw)
    success(f"Bid #{bid_id} still active: {fmt_amount(o[6])} remaining")

    # Cleanup
    send_tempo_tx(w3, account,
        calls=[Call.create(to=STABLECOIN_DEX, value=0,
                           data=encode_cancel_order(bid_id))],
        gas_limit=2_000_000)
    success("Cleaned up remaining bid")
    success("DEX limit order demonstration complete")


if __name__ == "__main__":
    main()
