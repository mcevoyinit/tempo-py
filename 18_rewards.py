#!/usr/bin/env python3
"""
18 — Token Reward Distribution & Claiming

Demonstrates TIP-20 reward distribution system:
- Holders opt in via setRewardRecipient()
- Anyone distributes rewards via distributeReward()
- Holders claim accrued rewards via claimRewards()

Rewards are split proportionally among opted-in holders
based on their token balance at distribution time.
"""
from tempo_utils import *
from eth_abi import decode as abi_decode


def main():
    header("18 · TOKEN REWARDS (DISTRIBUTE & CLAIM)")
    w3, account, chain_id = connect()
    dev2 = w3.eth.account.from_key(DEV2_KEY)

    section("1. Setup")
    token = ALPHA_USD
    kv("Token", read_string(w3, token, "name"))

    # Mint tokens to both accounts
    mint_amt = 1_000_000_000  # 1000 each
    for addr_name, addr in [("Dev1", account.address), ("Dev2", dev2.address)]:
        calldata = encode_mint(addr, mint_amt)
        send_tempo_tx(w3, account,
            calls=[Call.create(to=token, value=0, data=calldata)],
            gas_limit=500_000)
        bal = get_balance(w3, token, addr)
        kv(f"{addr_name} Bal", fmt_amount(bal))

    # ─── Opt In to Rewards ──────────────────────────────────
    section("2. Opt In to Rewards")

    # Dev1 opts in (set reward recipient to self)
    calldata = encode_set_reward_recipient(account.address)
    tx_hash, receipt, _ = send_tempo_tx(
        w3, account,
        calls=[Call.create(to=token, value=0, data=calldata)],
        gas_limit=2_000_000)
    kv("Dev1", f"Opted in (recipient = self)")
    tx_summary(tx_hash, receipt)

    # Dev2 opts in
    calldata = encode_set_reward_recipient(dev2.address)
    tx_hash, receipt, _ = send_tempo_tx(
        w3, dev2,
        calls=[Call.create(to=token, value=0, data=calldata)],
        gas_limit=2_000_000,
        private_key=DEV2_KEY)
    kv("Dev2", f"Opted in (recipient = self)")

    # Check opted-in supply
    raw = call_view(w3, token, encode_opted_in_supply())
    (opted,) = abi_decode(["uint128"], raw)
    kv("Opted-In Supply", fmt_amount(opted))
    success("Both holders opted into rewards")

    # ─── Distribute Rewards ─────────────────────────────────
    section("3. Distribute Reward")
    reward_amount = 500_000_000  # 500 tokens

    # Mint reward tokens to distributor (need tokens to distribute)
    calldata = encode_mint(account.address, reward_amount)
    send_tempo_tx(w3, account,
        calls=[Call.create(to=token, value=0, data=calldata)],
        gas_limit=500_000)

    calldata = encode_distribute_reward(reward_amount)
    tx_hash, receipt, _ = send_tempo_tx(
        w3, account,
        calls=[Call.create(to=token, value=0, data=calldata)],
        gas_limit=2_000_000)
    kv("Distributed", f"{fmt_amount(reward_amount)} tokens")
    tx_summary(tx_hash, receipt)

    # ─── Check Pending Rewards ──────────────────────────────
    section("4. Check Pending Rewards")
    for name, addr in [("Dev1", account.address), ("Dev2", dev2.address)]:
        raw = call_view(w3, token, encode_get_pending_rewards(addr))
        (pending,) = abi_decode(["uint128"], raw)
        kv(f"{name} Pending", fmt_amount(pending))
    success("Rewards accrued proportionally to balance")

    # ─── Claim Rewards ──────────────────────────────────────
    section("5. Claim Rewards (Dev1)")
    bal_before = get_balance(w3, token, account.address)

    calldata = encode_claim_rewards()
    tx_hash, receipt, _ = send_tempo_tx(
        w3, account,
        calls=[Call.create(to=token, value=0, data=calldata)],
        gas_limit=2_000_000)
    tx_summary(tx_hash, receipt)

    bal_after = get_balance(w3, token, account.address)
    claimed = bal_after - bal_before
    kv("Claimed", fmt_amount(claimed))

    # Check pending is now 0
    raw = call_view(w3, token, encode_get_pending_rewards(account.address))
    (pending,) = abi_decode(["uint128"], raw)
    kv("Pending After", fmt_amount(pending))
    if pending == 0:
        success("Dev1 claimed all pending rewards")

    # ─── Opt Out ────────────────────────────────────────────
    section("6. Opt Out of Rewards")
    # Dev1 opts out by setting recipient to zero address
    zero = "0x0000000000000000000000000000000000000000"
    calldata = encode_set_reward_recipient(zero)
    send_tempo_tx(w3, account,
        calls=[Call.create(to=token, value=0, data=calldata)],
        gas_limit=2_000_000)
    kv("Dev1", "Opted out (recipient = 0x0)")

    raw = call_view(w3, token, encode_opted_in_supply())
    (opted,) = abi_decode(["uint128"], raw)
    kv("Opted-In Supply", fmt_amount(opted))
    success("Dev1 opted out — only Dev2 remains")

    # Dev2 claims and opts out
    calldata = encode_claim_rewards()
    send_tempo_tx(w3, dev2,
        calls=[Call.create(to=token, value=0, data=calldata)],
        gas_limit=2_000_000,
        private_key=DEV2_KEY)
    calldata = encode_set_reward_recipient(zero)
    send_tempo_tx(w3, dev2,
        calls=[Call.create(to=token, value=0, data=calldata)],
        gas_limit=2_000_000,
        private_key=DEV2_KEY)
    success("Dev2 claimed and opted out")

    success("Token reward demonstration complete")


if __name__ == "__main__":
    main()
