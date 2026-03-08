#!/usr/bin/env python3
"""
Tempo Feature Showcase — Run All Demonstrations

Executes every Tempo feature demo script in sequence, tracking results.
Each script is independent and self-contained.

Usage:
  python run_all.py           # Run all demos
  python run_all.py 01 05 08  # Run specific demos by number
"""
import subprocess
import sys
import time

SCRIPTS = [
    ("01", "01_token_info.py",       "TIP-20 Token Info (Read-Only)"),
    ("02", "02_basic_transfer.py",   "Basic TIP-20 Transfer"),
    ("03", "03_batch_transfers.py",  "Batch Transfers (Atomic Multi-Call)"),
    ("04", "04_transfer_with_memo.py", "Transfer with Memo"),
    ("05", "05_token_creation.py",   "TIP-20 Token Creation"),
    ("06", "06_token_management.py", "Token Management (Mint/Burn/Roles)"),
    ("07", "07_parallel_nonces.py",  "Parallel Nonces (2D Nonce System)"),
    ("08", "08_fee_sponsorship.py",  "Fee Sponsorship (Gasless Tx)"),
    ("09", "09_access_keys.py",      "Access Keys (Account Keychain)"),
    ("10", "10_expiring_nonces.py",  "Expiring Nonces (TIP-1009)"),
    ("11", "11_policy_registry.py",  "TIP-403 Policy Registry"),
    ("12", "12_fee_amm.py",          "Fee AMM (Custom Fee Tokens)"),
    ("13", "13_dex_trading.py",      "DEX Limit Orders (CLOB Trading)"),
    ("14", "14_dex_swaps.py",        "DEX Market Swaps"),
    ("15", "15_dex_advanced.py",     "DEX Advanced (Flips/Ticks/Prices)"),
    ("16", "16_permit.py",           "EIP-2612 Permit (Gasless Approvals)"),
    ("17", "17_burn_blocked.py",     "Burn Blocked (Policy Enforcement)"),
    ("18", "18_rewards.py",          "Token Rewards (Distribute & Claim)"),
    ("19", "19_quote_token.py",      "Quote Token Management"),
    ("20", "20_compound_policies.py", "Compound Policies (TIP-1015)"),
    ("21", "21_fee_manager_liquidity.py", "Fee Manager Liquidity (AMM)"),
]

PYTHON = sys.executable
SCRIPT_DIR = "/Users/mcevoyinit/eric/tempo-local"

W = 62


def banner():
    print()
    print("╔" + "═" * (W - 2) + "╗")
    print("║" + "TEMPO FEATURE SHOWCASE".center(W - 2) + "║")
    print("║" + "Complete Blockchain Capability Demo".center(W - 2) + "║")
    print("╚" + "═" * (W - 2) + "╝")
    print()
    print("  Node:     http://localhost:9545")
    print("  Scripts:  /Users/mcevoyinit/eric/tempo-local/")
    print(f"  Demos:    {len(SCRIPTS)} features")
    print()


def run_script(num, filename, title):
    print()
    print("▓" * W)
    print(f"▓  DEMO {num}: {title}")
    print(f"▓  Script: {filename}")
    print("▓" * W)

    start = time.time()
    result = subprocess.run(
        [PYTHON, f"{SCRIPT_DIR}/{filename}"],
        capture_output=False,
        cwd=SCRIPT_DIR,
    )
    elapsed = time.time() - start

    return result.returncode, elapsed


def main():
    banner()

    # Filter scripts if specific numbers given
    if len(sys.argv) > 1:
        selected = set(sys.argv[1:])
        scripts = [(n, f, t) for n, f, t in SCRIPTS if n in selected]
        if not scripts:
            print(f"No matching demos. Available: {', '.join(n for n, _, _ in SCRIPTS)}")
            sys.exit(1)
    else:
        scripts = SCRIPTS

    results = []
    total_start = time.time()

    for num, filename, title in scripts:
        returncode, elapsed = run_script(num, filename, title)
        status = "PASS" if returncode == 0 else "FAIL"
        results.append((num, title, status, elapsed))

    total_elapsed = time.time() - total_start

    # ─── Summary ────────────────────────────────────────────────
    print()
    print()
    print("╔" + "═" * (W - 2) + "╗")
    print("║" + "RESULTS SUMMARY".center(W - 2) + "║")
    print("╚" + "═" * (W - 2) + "╝")
    print()

    passed = sum(1 for _, _, s, _ in results if s == "PASS")
    failed = sum(1 for _, _, s, _ in results if s == "FAIL")

    print(f"  {'#':<4} {'Demo':<38} {'Status':<6} {'Time':>6}")
    print(f"  {'─'*4} {'─'*38} {'─'*6} {'─'*6}")

    for num, title, status, elapsed in results:
        icon = "✓" if status == "PASS" else "✗"
        short_title = title[:36] + ".." if len(title) > 38 else title
        print(f"  {icon} {num}  {short_title:<38} {status:<6} {elapsed:5.1f}s")

    print(f"\n  Total: {passed} passed, {failed} failed, {total_elapsed:.1f}s elapsed")

    if failed == 0:
        print(f"\n  ✓ All {passed} Tempo feature demos passed!")
    else:
        print(f"\n  ✗ {failed} demo(s) had errors — check output above")

    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
