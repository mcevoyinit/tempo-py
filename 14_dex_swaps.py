#!/usr/bin/env python3
"""
14 — Stablecoin DEX: Market Swaps

Demonstrates swapping tokens against the on-chain orderbook.
Places ask orders to create liquidity, then executes swaps
with exact-in and exact-out semantics.
"""
from tempo_utils import *
from eth_abi import decode as abi_decode


def ensure_pair(w3, account):
    """Create pair if it doesn't exist."""
    try:
        send_tempo_tx(w3, account,
            calls=[Call.create(to=STABLECOIN_DEX, value=0,
                               data=encode_create_pair(ALPHA_USD))],
            gas_limit=2_000_000)
    except Exception:
        pass  # already exists


def main():
    header("14 · STABLECOIN DEX (MARKET SWAPS)")
    w3, account, chain_id = connect()

    section("1. Setup")
    ensure_pair(w3, account)
    approve_dex(w3, account)
    kv("Pair", "AlphaUSD / PathUSD")
    kv("AlphaUSD Bal", fmt_amount(get_balance(w3, ALPHA_USD, account.address)))
    kv("PathUSD Bal", fmt_amount(get_balance(w3, PATH_USD, account.address)))
    success("DEX approved for AlphaUSD + PathUSD")

    # ─── Place Ask Orders (Sell-Side Liquidity) ───────────────
    section("2. Build Sell-Side Liquidity")
    # Place 3 asks at different ticks to simulate depth
    asks = []
    for i, tick in enumerate([0, 10, 20]):
        amount = 500_000_000  # 500 tokens each
        raw = call_view(w3, STABLECOIN_DEX, encode_next_order_id())
        (oid,) = abi_decode(["uint128"], raw)
        asks.append(oid)

        calldata = encode_place(ALPHA_USD, amount, False, tick)
        tx_hash, receipt, _ = send_tempo_tx(
            w3, account,
            calls=[Call.create(to=STABLECOIN_DEX, value=0, data=calldata)],
            gas_limit=5_000_000,
        )
        price = (100_000 + tick) / 100_000
        kv(f"Ask #{oid}", f"{fmt_amount(amount)} @ tick={tick} (price={price:.4f})")

    success(f"3 ask orders placed, 1500 AlphaUSD on offer")

    # ─── Quote Swap ───────────────────────────────────────────
    section("3. Quote Swap (PathUSD → AlphaUSD)")
    swap_in = 200_000_000  # 200 PathUSD
    raw = call_view(w3, STABLECOIN_DEX,
                    encode_quote_swap_in(PATH_USD, ALPHA_USD, swap_in))
    (quote_out,) = abi_decode(["uint128"], raw)
    kv("Input", f"{fmt_amount(swap_in)} PathUSD")
    kv("Quoted Output", f"{fmt_amount(quote_out)} AlphaUSD")
    kv("Effective Price", f"{swap_in / quote_out:.6f}" if quote_out else "N/A")

    # ─── Execute Swap Exact-In ────────────────────────────────
    section("4. Swap Exact Amount In")
    alpha_before = get_balance(w3, ALPHA_USD, account.address)
    pusd_before = get_balance(w3, PATH_USD, account.address)

    calldata = encode_swap_exact_in(PATH_USD, ALPHA_USD, swap_in, 0)
    tx_hash, receipt, _ = send_tempo_tx(
        w3, account,
        calls=[Call.create(to=STABLECOIN_DEX, value=0, data=calldata)],
        gas_limit=5_000_000,
    )
    tx_summary(tx_hash, receipt)

    alpha_after = get_balance(w3, ALPHA_USD, account.address)
    pusd_after = get_balance(w3, PATH_USD, account.address)
    alpha_received = alpha_after - alpha_before
    pusd_spent = pusd_before - pusd_after

    kv("PathUSD Spent", fmt_amount(pusd_spent))
    kv("AlphaUSD Got", fmt_amount(alpha_received))
    if alpha_received > 0:
        success(f"Swap filled at effective price "
                f"{pusd_spent / alpha_received:.6f}")
    else:
        fail("No AlphaUSD received")

    # ─── Swap Exact Amount Out ────────────────────────────────
    section("5. Swap Exact Amount Out")
    want_out = 100_000_000  # Want exactly 100 AlphaUSD

    alpha_before = get_balance(w3, ALPHA_USD, account.address)
    pusd_before = get_balance(w3, PATH_USD, account.address)

    max_in = 150_000_000  # willing to pay up to 150 PathUSD
    calldata = encode_swap_exact_out(PATH_USD, ALPHA_USD, want_out, max_in)
    tx_hash, receipt, _ = send_tempo_tx(
        w3, account,
        calls=[Call.create(to=STABLECOIN_DEX, value=0, data=calldata)],
        gas_limit=5_000_000,
    )
    tx_summary(tx_hash, receipt)

    alpha_after = get_balance(w3, ALPHA_USD, account.address)
    pusd_after = get_balance(w3, PATH_USD, account.address)
    alpha_received = alpha_after - alpha_before
    pusd_spent = pusd_before - pusd_after

    kv("AlphaUSD Got", fmt_amount(alpha_received))
    kv("PathUSD Paid", fmt_amount(pusd_spent))
    if alpha_received == want_out:
        success(f"Got exact output of {fmt_amount(want_out)} AlphaUSD")

    # ─── Check DEX Internal Balance ───────────────────────────
    section("6. DEX Internal Balances")
    for token_name, token_addr in [("AlphaUSD", ALPHA_USD),
                                    ("PathUSD", PATH_USD)]:
        raw = call_view(w3, STABLECOIN_DEX,
                        encode_dex_balance(account.address, token_addr))
        (bal,) = abi_decode(["uint128"], raw)
        kv(f"{token_name}", fmt_amount(bal))
        if bal > 0:
            calldata = encode_dex_withdraw(token_addr, bal)
            send_tempo_tx(w3, account,
                calls=[Call.create(to=STABLECOIN_DEX, value=0,
                                   data=calldata)],
                gas_limit=2_000_000)
            success(f"Withdrew {fmt_amount(bal)} {token_name}")

    # ─── Cleanup remaining orders ─────────────────────────────
    section("7. Cleanup")
    cleaned = 0
    for oid in asks:
        try:
            raw = call_view(w3, STABLECOIN_DEX, encode_get_order(oid))
            o = abi_decode(["uint128"], raw[:32])
            if o[0] > 0:
                send_tempo_tx(w3, account,
                    calls=[Call.create(to=STABLECOIN_DEX, value=0,
                                       data=encode_cancel_order(oid))],
                    gas_limit=2_000_000)
                cleaned += 1
        except Exception:
            pass  # order already filled or cancelled
    kv("Orders Cleaned", cleaned)
    success("DEX swap demonstration complete")


if __name__ == "__main__":
    main()
