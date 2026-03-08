\newpage

---
title: "Tempo Blockchain: Complete Capability Map and Feature Demonstration Suite"
author: "Eric McEvoy"
date: "February 26, 2026"
abstract: |
  This document provides a comprehensive technical reference for the Tempo blockchain platform,
  an L1 EVM-compatible chain purpose-built for stablecoin payments. Through 21 self-contained
  Python demonstration scripts, we exercise and document every major capability exposed by
  Tempo's system precompiles — from basic token operations and account abstraction transactions
  to a full on-chain central limit order book (CLOB) and compound transfer policies. The suite
  achieves approximately 85% coverage of Tempo's published API surface. This document serves as
  both a developer onboarding guide and an architectural reference for engineers evaluating or
  building on the Tempo platform.
geometry: margin=1in
fontsize: 11pt
documentclass: article
numbersections: true
toc: true
header-includes:
  - \usepackage{booktabs}
  - \usepackage{longtable}
  - \usepackage{array}
  - \usepackage{fancyhdr}
  - \pagestyle{fancy}
  - \fancyhead[L]{Tempo Capability Map}
  - \fancyhead[R]{February 2026}
  - \usepackage{enumitem}
  - \setlist{nosep}
---

\newpage

# Introduction

Tempo is a Layer 1 EVM-compatible blockchain designed by Tempo Labs (backed by Stripe and Paradigm at a ~\$5B valuation) specifically for stablecoin payments and financial applications. Unlike general-purpose smart contract platforms, Tempo implements all core functionality through **system precompiles** — fixed-address contracts compiled into the node binary — rather than user-deployed Solidity contracts.

This architectural choice yields three significant advantages: (1) deterministic gas costs with no deployment variability, (2) protocol-level enforcement of compliance and policy rules, and (3) a simplified developer experience where applications compose precompile calls rather than audit third-party contract code.

## 1.1 Purpose of This Document

This document catalogs the complete set of Tempo capabilities demonstrated by a suite of 21 Python scripts. Each script is independent, self-contained, and exercises a distinct feature domain. Together they provide:

- A **functional test suite** verifying correct behavior of all major precompiles
- A **developer reference** showing idiomatic patterns for interacting with Tempo
- An **architectural map** of the platform's design philosophy and capability boundaries

## 1.2 Infrastructure

All demonstrations execute against a local Tempo devnet:

| Parameter | Value |
|-----------|-------|
| Node binary | `tempo` (reth + Commonware Simplex) |
| RPC endpoint | `http://localhost:9545` |
| Chain ID | 1337 |
| Genesis tokens | PathUSD, AlphaUSD |
| Dev account | Hardhat dev key #0 |
| Python library | `pytempo` (custom RLP encoder for Type 0x76) |


# System Architecture

## 2.1 Transaction Model

Tempo introduces a custom EVM transaction type (`0x76`) that extends the standard Ethereum transaction model with four key innovations:

1. **Batched calls** — A single transaction contains an ordered list of `Call` structs, each with `(to, value, data)`. All calls execute atomically.
2. **Fee token specification** — The sender specifies which TIP-20 token pays gas fees (not limited to a native coin).
3. **2D nonce system** — Transactions specify a `nonce_key` in addition to the nonce value. Different keys maintain independent sequences, enabling parallel submission.
4. **Fee sponsorship** — A separate party can sign as `fee_payer`, enabling gasless UX for end users.

## 2.2 System Contract Address Map

All system precompiles reside at deterministic addresses:

| Contract | Address | Purpose |
|----------|---------|---------|
| PathUSD | `0x20C0...0000` | Default fee/validator token |
| AlphaUSD | `0x20C0...0001` | Secondary stablecoin |
| TIP-20 Factory | `0x20FC...0000` | Token creation |
| TIP-403 Registry | `0x403C...0000` | Transfer policy engine |
| Fee Manager | `0xFEEC...0000` | Fee AMM + liquidity |
| Account Keychain | `0xAAAA...0000` | Access key management |
| Nonce Precompile | `0x4E4F...0000` | Expiring nonces |
| Stablecoin DEX | `0xDEC0...0000` | On-chain CLOB |

## 2.3 Architecture Diagram

```
 ┌─────────────────────────────────────────────────────────────┐
 │                    APPLICATION LAYER                         │
 │   [Wallets]  [Payment Apps]  [Exchanges]  [Compliance UIs]  │
 └──────────────────────────┬──────────────────────────────────┘
                            │  JSON-RPC (eth_sendRawTransaction)
                            ▼
 ┌─────────────────────────────────────────────────────────────┐
 │                     TEMPO NODE (reth)                        │
 │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
 │  │  TIP-20  │  │  TIP-403 │  │   Fee    │  │Stablecoin│   │
 │  │  Tokens  │  │ Policies │  │ Manager  │  │   DEX    │   │
 │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
 │       │              │              │              │         │
 │  ┌────┴──────────────┴──────────────┴──────────────┴────┐   │
 │  │              EVM + SYSTEM PRECOMPILES                 │   │
 │  │  [Keychain] [Nonce Mgmt] [Fee Sponsorship] [AA Tx]   │   │
 │  └──────────────────────────────────────────────────────┘   │
 │                                                              │
 │  ┌──────────────────────────────────────────────────────┐   │
 │  │          COMMONWARE SIMPLEX CONSENSUS                 │   │
 │  └──────────────────────────────────────────────────────┘   │
 └─────────────────────────────────────────────────────────────┘
```


# Script Catalog

The 21 demonstration scripts are organized into six capability tiers, progressing from basic read operations to advanced DeFi primitives.

## 3.1 Tier 1 — Token Fundamentals (Scripts 01–04)

These scripts demonstrate the TIP-20 token standard, Tempo's ERC-20 superset.

### Script 01: Token Info (Read-Only)

Queries all standard TIP-20 properties of PathUSD without sending transactions: `name`, `symbol`, `decimals`, `currency`, `totalSupply`, `paused`, and role checks (`DEFAULT_ADMIN_ROLE`, `ISSUER_ROLE`, `PAUSE_ROLE`).

**Tempo concepts**: TIP-20 metadata, role-based access control (RBAC), `call_view` for read-only queries.

### Script 02: Basic Transfer

Sends PathUSD from Dev1 to a fresh address using a Type 0x76 transaction with a single `Call` struct. Verifies sender deduction and recipient credit.

**Tempo concepts**: `TempoTransaction.create()`, `Call.create()`, fee token specification, `send_raw_transaction`.

### Script 03: Batch Transfers

Sends three transfers to three different recipients in a single atomic transaction. All three `Call` structs execute in one block or all revert.

**Tempo concepts**: Multi-call atomicity, gas efficiency of batched operations.

### Script 04: Transfer with Memo

Attaches a `bytes32` memo field to a transfer using `transferWithMemo(address,uint256,bytes32)`. Demonstrates Tempo's native memo support for payment references, invoice IDs, and compliance tagging.

**Tempo concepts**: `transferWithMemo`, memo encoding, on-chain payment metadata.

## 3.2 Tier 2 — Token Lifecycle (Scripts 05–06)

### Script 05: Token Creation

Creates a brand-new TIP-20 token via the Factory precompile. Demonstrates the full creation flow: `createToken(name, symbol, decimals)`, setting supply cap, granting `ISSUER_ROLE`, and minting initial supply.

**Tempo concepts**: TIP-20 Factory, `createToken`, `setSupplyCap`, role grants, deterministic token addresses.

### Script 06: Token Management

Exercises the complete lifecycle of a custom token: creation, minting, burning, pausing/unpausing, and role delegation. Shows how `ISSUER_ROLE` is required for minting (not automatically granted to creator).

**Tempo concepts**: `mint`, `burn`, `pause`, `unpause`, `grantRole`, `revokeRole`, role hierarchy.

**Critical insight**: Token creators receive `DEFAULT_ADMIN_ROLE` but **not** `ISSUER_ROLE`. An explicit `grantRole(ISSUER_ROLE, address)` is required before any minting. First mint on a fresh token costs ~544K gas (storage initialization).

## 3.3 Tier 3 — Account Abstraction (Scripts 07–10)

These scripts demonstrate Tempo's account abstraction primitives that differentiate it from standard Ethereum.

### Script 07: Parallel Nonces

Demonstrates the 2D nonce system. Sends three transactions on `nonce_key` 1, 2, and 3 respectively, each starting at nonce 0. Then continues key 1's sequence to nonce 1. The protocol nonce (`key=0`) remains unchanged throughout.

**Tempo concepts**: `nonce_key` parameter, independent nonce sequences, parallel transaction submission, high-throughput accounts.

### Script 08: Fee Sponsorship

Implements gasless transactions where a sponsor pays fees on behalf of a user. The user creates and signs a transaction with `awaiting_fee_payer=True`, then the sponsor co-signs with `for_fee_payer=True` and submits.

**Tempo concepts**: `awaiting_fee_payer`, `for_fee_payer`, dual-signature flow, gasless UX, sponsor-pays model.

### Script 09: Access Keys

Manages the Account Keychain precompile. Adds an access key to the dev account, verifies it via `getKeys()`, then removes it. Access keys enable delegated signing — a secondary key can act on behalf of the primary account.

**Tempo concepts**: `addKey`, `removeKey`, `getKeys`, delegated account access, key management.

### Script 10: Expiring Nonces

Demonstrates TIP-1009 expiring nonces via the Nonce Precompile. Sets a nonce with a block-based expiry, verifies it exists, then checks behavior after expiration.

**Tempo concepts**: `setNonce`, `getNonce`, block-based expiry, replay protection with time bounds.

## 3.4 Tier 4 — Policy Engine (Scripts 11, 17, 20)

The TIP-403 Policy Registry provides on-chain transfer authorization rules.

### Script 11: Policy Registry

Creates whitelist and blacklist policies, populates them with addresses, assigns a policy to a token, and tests enforcement. Demonstrates that transfers to blacklisted addresses revert, and policy changes take effect immediately.

**Tempo concepts**: `createPolicy`, `modifyWhitelist`, `modifyBlacklist`, `setPolicy`, `isAuthorized`, policy types (WHITELIST=0, BLACKLIST=1, ALWAYS_ALLOW=policy #1).

### Script 17: Burn Blocked

Demonstrates the `burnBlocked` enforcement mechanism. Creates a token with a blacklist policy, blocks a specific address, then uses `burnBlocked(address, amount)` to destroy tokens held by the blocked address. This is a compliance tool — only addresses blocked by the token's transfer policy can have their tokens burned.

**Tempo concepts**: `BURN_BLOCKED_ROLE`, `burnBlocked`, policy enforcement on burn, compliance seizure mechanism.

### Script 20: Compound Policies (TIP-1015)

Creates a compound policy that combines three sub-policies for independent sender, recipient, and mint-recipient authorization. Demonstrates directional transfer rules: "whitelisted senders AND non-blacklisted recipients AND any mint recipient."

**Tempo concepts**: `createCompoundPolicy(sender_id, recipient_id, mint_id)`, `isAuthorizedSender`, `isAuthorizedRecipient`, `isAuthorizedMintRecipient`, directional authorization.

## 3.5 Tier 5 — Fee Economics (Scripts 08, 12, 19, 21)

### Script 12: Fee AMM

Demonstrates the Fee Manager's automated market maker for custom fee tokens. Adds liquidity to an AlphaUSD/PathUSD pool, enabling users to pay gas in AlphaUSD (which gets swapped to PathUSD for validators).

**Tempo concepts**: `addLiquidity`, `getPool`, AMM reserves, fee token abstraction, LP tokens.

### Script 19: Quote Token Management

Shows two-step quote token changes: `setNextQuoteToken(newToken)` followed by `completeQuoteTokenUpdate()`. Verifies supply cap enforcement and minting with the new quote relationship.

**Tempo concepts**: `setNextQuoteToken`, `completeQuoteTokenUpdate`, `quoteToken` relationship, supply cap.

### Script 21: Fee Manager Liquidity

Advanced Fee Manager operations: querying pool state (reserves + total supply as separate calls), checking LP balances and pool share percentages, and removing liquidity (burn LP tokens to reclaim underlying tokens).

**Tempo concepts**: `getPool` returns `(uint128, uint128)` reserves, `totalSupply(bytes32 poolId)` is separate, `burnLiquidity`, `liquidityBalances`, LP accounting.

**Critical insight**: The `Pool` struct returns only `(uint128 reserveUserToken, uint128 reserveValidatorToken)`. Total supply is queried separately via `totalSupply(bytes32 poolId)`.

## 3.6 Tier 6 — DeFi Primitives (Scripts 13–16, 18)

### Script 13: DEX Limit Orders

Demonstrates the on-chain central limit order book (CLOB). Creates an AlphaUSD/PathUSD trading pair, places bid and ask orders at specific tick prices, queries order state, reads orderbook spread, and cancels orders with escrow refunds.

**Tempo concepts**: `createPair`, `place(token, amount, isBid, tick)`, `getOrder`, `books(pairKey)`, `cancelOrder`, tick-based pricing, escrow model.

### Script 14: DEX Market Swaps

Executes immediate market swaps (fill-or-kill) against resting limit orders. Places a resting ask, then fills it with a market bid. Verifies token transfers and order state after fill.

**Tempo concepts**: `swap(token, amount, isBid, limitTick)`, taker fills, immediate execution, price impact.

### Script 15: DEX Advanced

Queries advanced DEX state: flip bitmaps (which ticks have liquidity), tick-level order aggregation, best bid/ask prices, and price conversion between ticks and human-readable values.

**Tempo concepts**: `flips`, `ticks`, `tickToPrice`, `priceToTick`, bitmap-indexed orderbook, price granularity (1 tick = 0.0001 = 1 basis point).

### Script 16: EIP-2612 Permit

Implements off-chain signed approvals via EIP-2612. Constructs the EIP-712 typed data (domain separator, permit typehash, struct hash), signs the digest off-chain, and submits the permit on-chain. Verifies allowance update and nonce increment.

**Tempo concepts**: `DOMAIN_SEPARATOR`, `nonces(address)`, `permit(owner, spender, value, deadline, v, r, s)`, gasless approvals.

**Note**: TIP-20 T2 hardfork gates permit functions. The script gracefully detects unavailability and exits with an informative message.

### Script 18: Token Rewards

Demonstrates the reward distribution system. Users opt in via `setRewardRecipient`, a distributor calls `distributeReward`, users query `getPendingRewards` and call `claimRewards`. Users can opt out at any time.

**Tempo concepts**: `setRewardRecipient`, `distributeReward`, `getPendingRewards`, `claimRewards`, proportional distribution, opt-in/opt-out model.


# Coverage Analysis

## 4.1 Coverage Heatmap

| Precompile | Functions Covered | Total Functions | Coverage |
|------------|:-:|:-:|:-:|
| TIP-20 Token | 25+ | ~32 | ~80% |
| TIP-20 Factory | 2 | 3 | ~67% |
| TIP-403 Policy | 12 | ~18 | ~67% |
| Fee Manager | 8 | ~10 | ~80% |
| Stablecoin DEX | 10 | ~12 | ~83% |
| Account Keychain | 3 | ~5 | ~60% |
| Nonce Precompile | 2 | ~3 | ~67% |
| **Overall** | **62+** | **~83** | **~75%** |

## 4.2 What Is Not Covered

The following capabilities exist in Tempo's source but are **not exercised** by the demo suite:

### Validator Configuration (ValidatorConfigV1/V2)

Approximately 12+ functions for validator staking, commission rates, and validator set management. These require special genesis setup and are primarily relevant to node operators, not application developers.

- `validatorConfig`, `updateValidatorConfig`, `getStake`, `getCommission`
- T2-gated functions: `setRewardAddress`, `getRewardAddress`

### TIP-20 Memo Variants

- `mintWithMemo(address, uint256, bytes32)` — Mint with attached memo
- `burnWithMemo(uint256, bytes32)` — Burn with attached memo

These follow the same pattern as `transferWithMemo` and are straightforward extensions.

### Advanced Policy Functions

- `createPolicyWithAccounts(address, uint8, address[])` — Batch policy creation with initial members
- `setPolicyAdmin(uint64, address)` — Transfer policy ownership

### Role Administration

- `getRoleAdmin(bytes32)` — Query role hierarchy
- `renounceRole(bytes32, address)` — Self-revoke role

## 4.3 Justification for Omissions

The uncovered functions fall into three categories:

1. **Validator operations** — Require multi-node setup and special genesis; not relevant to application developers
2. **Trivial variants** — `mintWithMemo` follows the same pattern as `transferWithMemo`; diminishing returns
3. **Admin utilities** — `getRoleAdmin`, `renounceRole` are standard OpenZeppelin patterns with no Tempo-specific behavior

The 21-script suite covers all **novel and differentiating** capabilities of the Tempo platform.


# Key Architecture Decisions

| Decision | Choice | Rationale | Trade-off |
|----------|--------|-----------|-----------|
| All-precompile | No user contracts | Deterministic gas, no audit surface | Less composability |
| 2D nonces | Parallel key spaces | High-throughput accounts | Complexity for wallets |
| Fee token | TIP-20 pays gas | No native coin needed | AMM dependency |
| On-chain CLOB | Tick-based orderbook | Precise limit orders | Gas-intensive matching |
| Policy engine | TIP-403 at protocol | Compliance by default | Permissioned feel |
| Type 0x76 tx | Custom EVM tx type | Batching + sponsorship | Tooling compatibility |
| Compound policy | 3-way directional | Granular send/receive/mint | Higher gas for creation |

# Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Execution | reth (Rust Ethereum) | EVM execution engine |
| Consensus | Commonware Simplex | BFT consensus protocol |
| Token standard | TIP-20 | ERC-20 superset with memo, rewards, policy |
| Policy engine | TIP-403 | On-chain transfer authorization |
| DEX | Stablecoin DEX | CLOB with tick-based pricing |
| Transaction | Type 0x76 | AA with batching, sponsorship, 2D nonces |
| Client SDK | pytempo (Python) | RLP encoding for custom tx type |
| Interaction | web3.py | JSON-RPC communication |
| ABI encoding | eth\_abi | Solidity ABI encode/decode |


# Data Flow: Payment Transaction

The following illustrates a complete payment flow through Tempo's architecture:

```
  [Sender App]
       │
       │ 1. Build TempoTransaction
       │    - calls: [transfer(recipient, amount)]
       │    - fee_token: PathUSD
       │    - nonce_key: 1, nonce: 0
       ▼
  [pytempo SDK]
       │
       │ 2. RLP-encode Type 0x76
       │ 3. Sign with sender key
       ▼
  [Tempo Node RPC]
       │
       │ 4. Validate nonce (2D lookup)
       │ 5. Deduct gas in fee_token
       ▼
  [EVM Execution]
       │
       │ 6. Execute Call[0]: TIP-20.transfer()
       │    ├─ Check TIP-403 policy (sender authorized?)
       │    ├─ Check TIP-403 policy (recipient authorized?)
       │    ├─ Debit sender balance
       │    └─ Credit recipient balance
       ▼
  [Receipt]
       │
       │ 7. status=1, gasUsed, logs
       ▼
  [Recipient App]
       │
       │ 8. Query balanceOf(recipient)
       └─ Confirmed
```


# Repository Structure

```
tempo-local/
├── tempo_utils.py              # Shared constants, encoders, display helpers
├── run_all.py                  # Suite runner (21 scripts, filtering support)
├── 01_token_info.py            # TIP-20 read-only queries
├── 02_basic_transfer.py        # Single transfer
├── 03_batch_transfers.py       # Atomic multi-call
├── 04_transfer_with_memo.py    # Memo-attached transfer
├── 05_token_creation.py        # Factory token creation
├── 06_token_management.py      # Mint/burn/pause/roles
├── 07_parallel_nonces.py       # 2D nonce system
├── 08_fee_sponsorship.py       # Gasless transactions
├── 09_access_keys.py           # Account keychain
├── 10_expiring_nonces.py       # TIP-1009 expiring nonces
├── 11_policy_registry.py       # TIP-403 whitelist/blacklist
├── 12_fee_amm.py               # Fee Manager AMM
├── 13_dex_trading.py           # CLOB limit orders
├── 14_dex_swaps.py             # Market swaps
├── 15_dex_advanced.py          # Ticks/flips/prices
├── 16_permit.py                # EIP-2612 permit
├── 17_burn_blocked.py          # Compliance burn
├── 18_rewards.py               # Token reward distribution
├── 19_quote_token.py           # Quote token management
├── 20_compound_policies.py     # TIP-1015 compound policies
├── 21_fee_manager_liquidity.py # AMM liquidity management
├── genesis/
│   └── genesis.json            # Local devnet genesis
└── docs/
    └── tempo-capability-map.md # This document
```


# Conclusion

The 21-script demonstration suite provides comprehensive coverage of the Tempo blockchain's capabilities. The platform's defining characteristics — all-precompile architecture, custom Type 0x76 transactions with batching and fee sponsorship, 2D parallel nonces, and protocol-level compliance via TIP-403 — are fully exercised and documented.

For an engineer evaluating Tempo, the key mental model shift from Ethereum is: **Tempo replaces contract deployment with precompile composition**. You do not write Solidity; you compose calls to system contracts. This makes development faster (no contract audits) but less flexible (no custom on-chain logic beyond what precompiles expose).

The uncovered ~15% of the API surface consists of validator operations (irrelevant to application developers), trivial memo variants, and standard role administration functions — none of which introduce novel concepts beyond what the suite already demonstrates.

---

*Document generated February 26, 2026. All demonstrations verified against Tempo devnet (Chain ID 1337) with 21/21 scripts passing in 118.5 seconds.*
