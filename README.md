# tempo-py

Python examples for the [Tempo](https://tempo.xyz) blockchain. 21 scripts covering TIP-20 tokens, account abstraction, fee sponsorship, DEX trading, compliance policies, and more.

## Scripts

| Script | What it does |
|--------|-------------|
| `01_token_info.py` | Read TIP-20 token metadata without sending transactions |
| `02_basic_transfer.py` | TIP-20 token transfer via Type 0x76 AA transaction |
| `03_batch_transfers.py` | Batch multiple operations into a single atomic transaction |
| `04_transfer_with_memo.py` | Attach a 32-byte memo for payment tracking |
| `05_token_creation.py` | Create new TIP-20 stablecoins via the Factory precompile |
| `06_token_management.py` | Admin operations: mint, burn, roles, pause |
| `07_parallel_nonces.py` | 2D nonce system for parallel transaction execution |
| `08_fee_sponsorship.py` | Gasless transactions with a sponsor paying fees |
| `09_access_keys.py` | Secondary keys with expiry, spending limits, signature flexibility |
| `10_expiring_nonces.py` | Time-windowed transactions with replay protection |
| `11_policy_registry.py` | On-chain compliance via TIP-403 transfer policies |
| `12_fee_amm.py` | Pay fees in non-default stablecoins with automatic swaps |
| `13_dex_trading.py` | Trade on the on-chain central limit order book (CLOB) |
| `14_dex_swaps.py` | Market swaps against the on-chain orderbook |
| `15_dex_advanced.py` | Advanced DEX: flip orders, tick levels, price math |
| `16_permit.py` | Gasless approvals via EIP-2612 permit signatures |
| `17_burn_blocked.py` | Enforce burning of blacklisted address tokens |
| `18_rewards.py` | Distribute and claim rewards among opted-in holders |
| `19_quote_token.py` | Change a token's quote token (two-step admin) |
| `20_compound_policies.py` | Directional transfer policies with sender/recipient rules |
| `21_fee_manager_liquidity.py` | Query pool state and remove Fee Manager AMM liquidity |

### Utilities

| File | Purpose |
|------|---------|
| `tempo_utils.py` | ABI encoding, transaction helpers, display formatting, system contract addresses |
| `send_tx.py` | Send Tempo AA transactions on a local 2-node network |
| `run_all.py` | Execute all scripts in sequence |
| `vellum_on_tempo.py` | Persistence proof-of-concept with on-chain hash notarization |

## Setup

```bash
pip install web3 eth-account
```

Scripts target a local Tempo devnet (2-node setup). All keys are standard Hardhat/Anvil dev keys.

## What's Tempo?

Payments blockchain backed by Stripe and Paradigm. Native account abstraction, TIP-20 stablecoin standard, fee sponsorship, on-chain CLOB, and compliance primitives.

## License

MIT
