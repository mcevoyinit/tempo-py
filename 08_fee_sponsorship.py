#!/usr/bin/env python3
"""
08 — Fee Sponsorship (Gasless Transactions)

Demonstrates Tempo's fee sponsorship model where a sponsor pays gas fees
on behalf of a user. This enables gasless UX — users transact without
holding any fee tokens.

Flow:
  1. User creates tx with awaiting_fee_payer=True
  2. User signs the transaction
  3. Sponsor signs with for_fee_payer=True
  4. Sponsor submits the fully-signed transaction
"""
import sys
sys.path.insert(0, "/Users/mcevoyinit/eric/pytempo")

from tempo_utils import *
from pytempo import TempoTransaction, Call


def main():
    header("08 · FEE SPONSORSHIP")
    w3, dev_account, chain_id = connect()

    section("Setup Accounts")

    # The dev account is our sponsor (has PathUSD for gas)
    sponsor = dev_account
    sponsor_key = DEV_PRIVATE_KEY

    # Create a "user" account and fund it with tokens (but sponsor pays gas)
    user_acct = w3.eth.account.create()
    user_key = "0x" + user_acct.key.hex()
    user_addr = user_acct.address

    kv("Sponsor", sponsor.address[:24] + "...")
    kv("User", user_addr[:24] + "...")

    # Fund user with some PathUSD via dev account
    fund_amount = 5_000_000  # 5 PathUSD
    calldata = encode_transfer(user_addr, fund_amount)
    send_tempo_tx(
        w3, dev_account,
        calls=[Call.create(to=PATH_USD, value=0, data=calldata)],
    )

    user_bal = get_balance(w3, PATH_USD, user_addr)
    kv("User PathUSD", fmt_amount(user_bal))

    # The user wants to send tokens but have the sponsor pay gas
    recipient = w3.eth.account.create().address
    send_amount = 1_000_000  # 1 PathUSD
    kv("Recipient", recipient[:24] + "...")
    kv("Send Amount", fmt_amount(send_amount))

    section("Building Sponsored Transaction")
    gas_price = w3.eth.gas_price or 20_000_000_000
    user_nonce = w3.eth.get_transaction_count(user_addr)

    transfer_data = encode_transfer(recipient, send_amount)

    tx = TempoTransaction.create(
        chain_id=chain_id,
        gas_limit=1_000_000,
        max_fee_per_gas=gas_price * 3,
        max_priority_fee_per_gas=gas_price,
        nonce=user_nonce,
        fee_token=PATH_USD,
        calls=(Call.create(to=PATH_USD, value=0, data=transfer_data),),
        awaiting_fee_payer=True,
    )

    print("  1. User creates tx with awaiting_fee_payer=True")

    # Step 1: User signs
    user_signed = tx.sign(user_key)
    print("  2. User signs the transaction")

    # Step 2: Sponsor signs as fee payer
    fully_signed = user_signed.sign(sponsor_key, for_fee_payer=True)
    print("  3. Sponsor signs with for_fee_payer=True")

    section("Submitting Sponsored Transaction")
    sponsor_before = get_balance(w3, PATH_USD, sponsor.address)
    user_before = get_balance(w3, PATH_USD, user_addr)

    tx_hash = w3.eth.send_raw_transaction(fully_signed.encode())
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
    tx_summary(tx_hash, receipt)

    section("Balance Changes")
    sponsor_after = get_balance(w3, PATH_USD, sponsor.address)
    user_after = get_balance(w3, PATH_USD, user_addr)
    recip_bal = get_balance(w3, PATH_USD, recipient)

    sponsor_diff = sponsor_before - sponsor_after
    user_diff = user_before - user_after

    kv("Sponsor Paid (gas)", fmt_amount(sponsor_diff))
    kv("User Paid", fmt_amount(user_diff))
    kv("Recipient Got", fmt_amount(recip_bal))

    section("Verification")
    if recip_bal == send_amount:
        success("Recipient received tokens")
    else:
        fail(f"Expected {fmt_amount(send_amount)}, got {fmt_amount(recip_bal)}")

    if user_diff == send_amount:
        success("User only paid the transfer amount (zero gas)")
    else:
        print(f"  ! User diff: {fmt_amount(user_diff)} (expected {fmt_amount(send_amount)})")

    if sponsor_diff > 0 and sponsor_diff != send_amount:
        success(f"Sponsor paid {fmt_amount(sponsor_diff)} in gas fees")

    success("Fee sponsorship complete — gasless UX demonstrated")


if __name__ == "__main__":
    main()
