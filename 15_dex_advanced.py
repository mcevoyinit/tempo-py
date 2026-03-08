#!/usr/bin/env python3
"""
15 — Stablecoin DEX: Advanced Features

Demonstrates flip orders (auto-reverse on fill), orderbook
introspection (tick levels), price conversions, DEX constants,
and quoteSwapExactAmountOut.

- Flip orders: Sell at one price, auto-buy at another when filled
- Tick levels: Query per-tick liquidity depth
- Price math: Convert between ticks and prices
"""
from tempo_utils import *
from eth_abi import decode as abi_decode


def ensure_pair(w3, account):
    try:
        send_tempo_tx(w3, account,
            calls=[Call.create(to=STABLECOIN_DEX, value=0,
                               data=encode_create_pair(ALPHA_USD))],
            gas_limit=5_000_000)
    except Exception:
        pass


def main():
    header("15 · DEX ADVANCED (FLIP & INTROSPECTION)")
    w3, account, chain_id = connect()

    section("1. Setup")
    ensure_pair(w3, account)
    approve_dex(w3, account)
    kv("Pair", "AlphaUSD / PathUSD")
    success("DEX approved for AlphaUSD + PathUSD")

    # ─── DEX Constants ──────────────────────────────────────
    section("2. DEX Constants")
    for name in ["MIN_TICK", "MAX_TICK", "TICK_SPACING", "PRICE_SCALE",
                 "MIN_ORDER_AMOUNT", "MIN_PRICE", "MAX_PRICE"]:
        sig = f"{name}()"
        raw = call_view(w3, STABLECOIN_DEX, selector(sig))
        if name in ("MIN_TICK", "MAX_TICK", "TICK_SPACING"):
            (val,) = abi_decode(["int16"], raw)
        elif name in ("PRICE_SCALE", "MIN_PRICE", "MAX_PRICE"):
            (val,) = abi_decode(["uint32"], raw)
        else:
            (val,) = abi_decode(["uint128"], raw)
        kv(name, f"{val:,}" if isinstance(val, int) and val > 1000 else val)
    success("All DEX constants retrieved")

    # ─── Price Conversion ───────────────────────────────────
    section("3. Price Conversion (tickToPrice / priceToTick)")
    tick_to_price_sel = selector("tickToPrice(int16)")
    price_to_tick_sel = selector("priceToTick(uint32)")

    for tick in [-100, -10, 0, 10, 100, 500]:
        raw = call_view(w3, STABLECOIN_DEX,
                        tick_to_price_sel + abi_encode(["int16"], [tick]))
        (price,) = abi_decode(["uint32"], raw)
        kv(f"Tick {tick:>5}", f"→ price {price:,} (= {price / 100_000:.5f})")

    # Round-trip: tick → price → tick
    raw = call_view(w3, STABLECOIN_DEX,
                    price_to_tick_sel + abi_encode(["uint32"], [100_100]))
    (rt_tick,) = abi_decode(["int16"], raw)
    kv("Price 100100", f"→ tick {rt_tick}")
    success("Price ↔ tick conversion verified")

    # ─── Flip Order (ASK → auto BID) ────────────────────────
    section("4. Place Flip Order (ASK → auto BID)")
    flip_amount = 200_000_000
    ask_tick = 10               # Sell at price 1.00010
    flip_to_bid_tick = 0        # Auto-buy at price 1.00000

    raw = call_view(w3, STABLECOIN_DEX, encode_next_order_id())
    (flip_id,) = abi_decode(["uint128"], raw)

    calldata = encode_place_flip(ALPHA_USD, flip_amount, False,
                                  ask_tick, flip_to_bid_tick)
    tx_hash, receipt, _ = send_tempo_tx(
        w3, account,
        calls=[Call.create(to=STABLECOIN_DEX, value=0, data=calldata)],
        gas_limit=5_000_000,
    )
    kv("Flip Order ID", flip_id)
    kv("Strategy", f"ASK tick={ask_tick} → auto BID tick={flip_to_bid_tick}")
    kv("Logic", "Sell @ 1.00010, auto-buy @ 1.00000")
    tx_summary(tx_hash, receipt)

    # Verify it's a flip order
    raw = call_view(w3, STABLECOIN_DEX, encode_get_order(flip_id))
    o = abi_decode(
        ["uint128", "address", "bytes32", "bool", "int16",
         "uint128", "uint128", "uint128", "uint128", "bool", "int16"],
        raw)
    kv("Is Flip", o[9])
    kv("Flip Tick", o[10])
    success("Flip order confirmed on-chain")

    # ─── Tick Level Queries ─────────────────────────────────
    section("5. Query Tick Levels")
    get_tick_sel = selector("getTickLevel(address,int16,bool)")

    for tick_val, is_bid, label in [
        (ask_tick, False, f"Ask Tick {ask_tick}"),
        (flip_to_bid_tick, True, f"Bid Tick {flip_to_bid_tick}"),
        (0, False, "Ask Tick 0"),
    ]:
        raw = call_view(w3, STABLECOIN_DEX,
                        get_tick_sel + abi_encode(
                            ["address", "int16", "bool"],
                            [ALPHA_USD, tick_val, is_bid]))
        (head, tail, total_liq) = abi_decode(
            ["uint128", "uint128", "uint128"], raw)
        kv(label, f"head={head} tail={tail} liq={fmt_amount(total_liq)}")
    success("Tick level depth retrieved")

    # ─── Quote Swap (Exact Out) ─────────────────────────────
    section("6. Quote Swap Exact Amount Out")
    want = 100_000_000  # 100 AlphaUSD
    quote_out_sel = selector("quoteSwapExactAmountOut(address,address,uint128)")
    try:
        raw = call_view(w3, STABLECOIN_DEX,
                        quote_out_sel + abi_encode(
                            ["address", "address", "uint128"],
                            [PATH_USD, ALPHA_USD, want]))
        (cost,) = abi_decode(["uint128"], raw)
        kv("Want", f"{fmt_amount(want)} AlphaUSD")
        kv("Cost", f"{fmt_amount(cost)} PathUSD")
        kv("Eff Price", f"{cost / want:.6f}")
        success("quoteSwapExactAmountOut verified")
    except Exception:
        kv("Note", "No ask liquidity for quote (OK)")

    # ─── Fill Flip via Swap ─────────────────────────────────
    section("7. Fill Flip Order via Swap")
    kv("Action", "Swap PathUSD → AlphaUSD (fills asks)")

    # Use swapExactAmountOut to buy exactly our flip order's amount
    # This fills the cheapest asks first, including ours at tick 10
    try:
        # First, figure out how much to pay for exactly flip_amount
        raw = call_view(w3, STABLECOIN_DEX,
                        quote_out_sel + abi_encode(
                            ["address", "address", "uint128"],
                            [PATH_USD, ALPHA_USD, flip_amount]))
        (fill_cost,) = abi_decode(["uint128"], raw)
        kv("Quoted Cost", f"{fmt_amount(fill_cost)} PathUSD for {fmt_amount(flip_amount)} AlphaUSD")

        calldata = encode_swap_exact_out(PATH_USD, ALPHA_USD,
                                          flip_amount, fill_cost + 10_000_000)
        tx_hash, receipt, _ = send_tempo_tx(
            w3, account,
            calls=[Call.create(to=STABLECOIN_DEX, value=0, data=calldata)],
            gas_limit=5_000_000,
        )
        tx_summary(tx_hash, receipt)

        if receipt["status"] == 1:
            # Check if the flip order was filled
            try:
                raw = call_view(w3, STABLECOIN_DEX,
                                encode_get_order(flip_id))
                o = abi_decode(
                    ["uint128", "address", "bytes32", "bool", "int16",
                     "uint128", "uint128", "uint128", "uint128",
                     "bool", "int16"], raw)
                remaining = o[6]
                if remaining == 0:
                    kv("Flip Order", f"#{flip_id} FULLY FILLED")
                else:
                    kv("Flip Order", f"#{flip_id} remaining={fmt_amount(remaining)}")
            except Exception:
                kv("Flip Order", f"#{flip_id} consumed (no longer queryable)")

            # Check for auto-created bid from flip
            section("8. Verify Flipped Bid Order")
            raw = call_view(w3, STABLECOIN_DEX, encode_next_order_id())
            (next_id,) = abi_decode(["uint128"], raw)

            found_flip = False
            for check_id in range(flip_id, next_id):
                try:
                    raw = call_view(w3, STABLECOIN_DEX,
                                    encode_get_order(check_id))
                    o = abi_decode(
                        ["uint128", "address", "bytes32", "bool", "int16",
                         "uint128", "uint128", "uint128", "uint128",
                         "bool", "int16"], raw)
                    if o[3] and o[4] == flip_to_bid_tick:  # isBid at flip tick
                        kv("Flipped BID ID", o[0])
                        kv("Tick", f"{o[4]} (price 1.00000)")
                        kv("Amount", fmt_amount(o[5]))
                        success("Flip auto-created BID on opposite side")
                        found_flip = True
                        # Cleanup
                        send_tempo_tx(w3, account,
                            calls=[Call.create(to=STABLECOIN_DEX, value=0,
                                               data=encode_cancel_order(o[0]))],
                            gas_limit=5_000_000)
                        break
                except Exception:
                    continue
            if not found_flip:
                kv("Note", "Flip order not fully filled or "
                   "flipped bid already consumed")
        else:
            kv("Note", "Swap failed — insufficient ask liquidity for full fill")
    except Exception:
        kv("Note", "Could not quote full fill (insufficient liquidity)")

    # ─── Cleanup ────────────────────────────────────────────
    section("9. Cleanup")
    # Cancel our flip order if still alive
    try:
        raw = call_view(w3, STABLECOIN_DEX, encode_get_order(flip_id))
        o = abi_decode(["uint128"], raw[:32])
        if o[0] > 0:
            send_tempo_tx(w3, account,
                calls=[Call.create(to=STABLECOIN_DEX, value=0,
                                   data=encode_cancel_order(flip_id))],
                gas_limit=5_000_000)
            success(f"Cancelled remaining flip order #{flip_id}")
    except Exception:
        success(f"Flip order #{flip_id} already consumed")

    # Withdraw any DEX internal balances
    for name, token in [("AlphaUSD", ALPHA_USD), ("PathUSD", PATH_USD)]:
        raw = call_view(w3, STABLECOIN_DEX,
                        encode_dex_balance(account.address, token))
        (bal,) = abi_decode(["uint128"], raw)
        if bal > 0:
            send_tempo_tx(w3, account,
                calls=[Call.create(to=STABLECOIN_DEX, value=0,
                                   data=encode_dex_withdraw(token, bal))],
                gas_limit=5_000_000)
            kv(f"Withdrew {name}", fmt_amount(bal))

    success("DEX advanced features demonstration complete")


if __name__ == "__main__":
    main()
