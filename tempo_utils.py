"""
Shared utilities for Tempo feature demonstration scripts.

Provides constants, ABI encoding/decoding, display formatting,
and connection helpers used across all demo scripts.
"""
import sys
import time

sys.path.insert(0, "/Users/mcevoyinit/eric/pytempo")

from web3 import Web3
from eth_abi import encode as abi_encode, decode as abi_decode

from pytempo import Call, TempoTransaction

# ─── Network & Accounts ────────────────────────────────────────
NODE1_RPC = "http://localhost:9545"
NODE2_RPC = "http://localhost:9546"
DEV_PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"

# ─── System Contract Addresses ──────────────────────────────────
PATH_USD = Web3.to_checksum_address("0x20c0000000000000000000000000000000000000")
TIP20_FACTORY = Web3.to_checksum_address("0x20FC000000000000000000000000000000000000")
TIP_FEE_MANAGER = Web3.to_checksum_address("0xfeec000000000000000000000000000000000000")
ACCOUNT_KEYCHAIN = Web3.to_checksum_address("0xaAAAaaAA00000000000000000000000000000000")
TIP403_REGISTRY = Web3.to_checksum_address("0x403C000000000000000000000000000000000000")
NONCE_PRECOMPILE = Web3.to_checksum_address("0x4E4F4E4345000000000000000000000000000000")
STABLECOIN_DEX = Web3.to_checksum_address("0xdec0000000000000000000000000000000000000")

# ─── TIP-20 Role Hashes ────────────────────────────────────────
ISSUER_ROLE = Web3.keccak(text="ISSUER_ROLE")
PAUSE_ROLE = Web3.keccak(text="PAUSE_ROLE")
UNPAUSE_ROLE = Web3.keccak(text="UNPAUSE_ROLE")
DEFAULT_ADMIN_ROLE = Web3.keccak(text="DEFAULT_ADMIN_ROLE")
BURN_BLOCKED_ROLE = Web3.keccak(text="BURN_BLOCKED_ROLE")

# ─── Function Selectors ────────────────────────────────────────
SEL = {}

def _sel(sig):
    """Compute and cache 4-byte function selector."""
    if sig not in SEL:
        SEL[sig] = Web3.keccak(text=sig)[:4]
    return SEL[sig]


def selector(sig):
    """Public alias for computing 4-byte function selectors."""
    return _sel(sig)


# ─── ABI Encoding Helpers ──────────────────────────────────────

def encode_transfer(recipient: str, amount: int) -> bytes:
    sel = _sel("transfer(address,uint256)")
    return sel + abi_encode(["address", "uint256"], [recipient, amount])


def encode_transfer_with_memo(recipient: str, amount: int, memo: bytes) -> bytes:
    sel = _sel("transferWithMemo(address,uint256,bytes32)")
    return sel + abi_encode(["address", "uint256", "bytes32"], [recipient, amount, memo])


def encode_approve(spender: str, amount: int) -> bytes:
    sel = _sel("approve(address,uint256)")
    return sel + abi_encode(["address", "uint256"], [spender, amount])


def encode_mint(to: str, amount: int) -> bytes:
    sel = _sel("mint(address,uint256)")
    return sel + abi_encode(["address", "uint256"], [to, amount])


def encode_burn(amount: int) -> bytes:
    sel = _sel("burn(uint256)")
    return sel + abi_encode(["uint256"], [amount])


def encode_grant_role(role: bytes, account: str) -> bytes:
    sel = _sel("grantRole(bytes32,address)")
    return sel + abi_encode(["bytes32", "address"], [role, account])


def encode_has_role(role: bytes, account: str) -> bytes:
    # Tempo uses (address, bytes32) order — reversed from OpenZeppelin
    sel = _sel("hasRole(address,bytes32)")
    return sel + abi_encode(["address", "bytes32"], [account, role])


def encode_pause() -> bytes:
    return _sel("pause()")


def encode_unpause() -> bytes:
    return _sel("unpause()")


def encode_create_token(name: str, symbol: str, currency: str,
                        quote_token: str, admin: str, salt: bytes) -> bytes:
    sel = _sel("createToken(string,string,string,address,address,bytes32)")
    return sel + abi_encode(
        ["string", "string", "string", "address", "address", "bytes32"],
        [name, symbol, currency, quote_token, admin, salt],
    )


def encode_set_user_token(token: str) -> bytes:
    sel = _sel("setUserToken(address)")
    return sel + abi_encode(["address"], [token])


def encode_add_liquidity(user_token: str, validator_token: str,
                         amount_validator_token: int, to: str) -> bytes:
    sel = _sel("mint(address,address,uint256,address)")
    return sel + abi_encode(
        ["address", "address", "uint256", "address"],
        [user_token, validator_token, amount_validator_token, to],
    )


def encode_create_policy(admin: str, policy_type: int) -> bytes:
    sel = _sel("createPolicy(address,uint8)")
    return sel + abi_encode(["address", "uint8"], [admin, policy_type])


def encode_modify_whitelist(policy_id: int, account: str, allowed: bool) -> bytes:
    sel = _sel("modifyPolicyWhitelist(uint64,address,bool)")
    return sel + abi_encode(["uint64", "address", "bool"], [policy_id, account, allowed])


def encode_is_authorized(policy_id: int, user: str) -> bytes:
    sel = _sel("isAuthorized(uint64,address)")
    return sel + abi_encode(["uint64", "address"], [policy_id, user])


def encode_policy_id_counter() -> bytes:
    return _sel("policyIdCounter()")


def encode_authorize_key(key_id: str, sig_type: int, expiry: int,
                         enforce_limits: bool, limits: list) -> bytes:
    sel = _sel("authorizeKey(address,uint8,uint64,bool,(address,uint256)[])")
    return sel + abi_encode(
        ["address", "uint8", "uint64", "bool", "(address,uint256)[]"],
        [key_id, sig_type, expiry, enforce_limits, limits],
    )


def encode_revoke_key(key_id: str) -> bytes:
    sel = _sel("revokeKey(address)")
    return sel + abi_encode(["address"], [key_id])


def encode_get_key(account: str, key_id: str) -> bytes:
    sel = _sel("getKey(address,address)")
    return sel + abi_encode(["address", "address"], [account, key_id])


def encode_get_remaining_limit(account: str, key_id: str, token: str) -> bytes:
    sel = _sel("getRemainingLimit(address,address,address)")
    return sel + abi_encode(["address", "address", "address"], [account, key_id, token])


# ─── Read Helpers (eth_call) ───────────────────────────────────

def call_view(w3, to: str, data: bytes) -> bytes:
    """Execute a read-only call and return raw result bytes."""
    result = w3.eth.call({"to": to, "data": "0x" + data.hex()})
    return bytes(result)


def read_string(w3, token: str, func: str) -> str:
    data = _sel(f"{func}()")
    raw = call_view(w3, token, data)
    if len(raw) == 0:
        return ""
    (val,) = abi_decode(["string"], raw)
    return val


def read_uint256(w3, token: str, func: str) -> int:
    data = _sel(f"{func}()")
    raw = call_view(w3, token, data)
    if len(raw) == 0:
        return 0
    (val,) = abi_decode(["uint256"], raw)
    return val


def read_uint8(w3, token: str, func: str) -> int:
    data = _sel(f"{func}()")
    raw = call_view(w3, token, data)
    if len(raw) == 0:
        return 0
    (val,) = abi_decode(["uint8"], raw)
    return val


def read_bool(w3, token: str, func: str) -> bool:
    data = _sel(f"{func}()")
    raw = call_view(w3, token, data)
    if len(raw) == 0:
        return False
    (val,) = abi_decode(["bool"], raw)
    return val


def get_balance(w3, token: str, account: str) -> int:
    sel = _sel("balanceOf(address)")
    data = sel + abi_encode(["address"], [account])
    raw = call_view(w3, token, data)
    if len(raw) == 0:
        return 0
    (val,) = abi_decode(["uint256"], raw)
    return val


# ─── Transaction Helpers ───────────────────────────────────────

def connect(rpc_url=NODE1_RPC):
    """Connect to Tempo node and return (w3, account, chain_id)."""
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    assert w3.is_connected(), f"Cannot connect to {rpc_url}"
    account = w3.eth.account.from_key(DEV_PRIVATE_KEY)
    return w3, account, w3.eth.chain_id


def send_tempo_tx(w3, account, calls, gas_limit=1_000_000, nonce=None,
                  nonce_key=0, fee_token=None, awaiting_fee_payer=False,
                  valid_before=None, valid_after=None, private_key=None):
    """Build, sign, send a Tempo AA transaction and wait for receipt."""
    if fee_token is None:
        fee_token = PATH_USD
    if nonce is None:
        nonce = w3.eth.get_transaction_count(account.address)
    gas_price = w3.eth.gas_price or 20_000_000_000

    tx = TempoTransaction.create(
        chain_id=w3.eth.chain_id,
        gas_limit=gas_limit,
        max_fee_per_gas=gas_price * 10,
        max_priority_fee_per_gas=gas_price * 2,
        nonce=nonce,
        nonce_key=nonce_key,
        fee_token=fee_token,
        calls=tuple(calls),
        awaiting_fee_payer=awaiting_fee_payer,
        valid_before=valid_before,
        valid_after=valid_after,
    )

    key = private_key or DEV_PRIVATE_KEY
    signed = tx.sign(key)
    tx_hash = w3.eth.send_raw_transaction(signed.encode())
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
    return tx_hash, receipt, tx


def fund_account(w3, address):
    """Fund an account via the Tempo faucet RPC."""
    try:
        w3.provider.make_request("tempo_fundAddress", [address])
        time.sleep(2)
        return True
    except Exception:
        return False


# ─── Display Helpers ───────────────────────────────────────────

WIDTH = 62


def header(title):
    print(f"\n╔{'═' * (WIDTH - 2)}╗")
    print(f"║{title:^{WIDTH - 2}}║")
    print(f"╚{'═' * (WIDTH - 2)}╝")


def section(title):
    pad = WIDTH - 5 - len(title)
    print(f"\n─── {title} {'─' * max(pad, 1)}")


def kv(key, value, indent=2):
    prefix = " " * indent
    print(f"{prefix}{key + ':':<22} {value}")


def success(msg):
    print(f"  ✓ {msg}")


def fail(msg):
    print(f"  ✗ {msg}")


def tx_summary(tx_hash, receipt):
    status = "SUCCESS" if receipt["status"] == 1 else "FAILED"
    kv("Status", status)
    kv("Tx Hash", tx_hash.hex()[:20] + "...")
    kv("Block", receipt["blockNumber"])
    kv("Gas Used", f"{receipt['gasUsed']:,}")


def divider():
    print("─" * WIDTH)


def fmt_amount(amount, decimals=6):
    """Format a token amount with decimals."""
    if amount == 0:
        return "0"
    whole = amount // (10 ** decimals)
    frac = amount % (10 ** decimals)
    if frac == 0:
        return f"{whole:,}"
    return f"{whole:,}.{str(frac).zfill(decimals).rstrip('0')}"


# ─── Additional Addresses ─────────────────────────────────────
ALPHA_USD = Web3.to_checksum_address("0x20C0000000000000000000000000000000000001")
BETA_USD  = Web3.to_checksum_address("0x20C0000000000000000000000000000000000002")
THETA_USD = Web3.to_checksum_address("0x20C0000000000000000000000000000000000003")

# ─── Additional Roles ─────────────────────────────────────────
BURN_AT_ROLE = Web3.keccak(text="BURN_AT_ROLE")

# ─── Additional Test Account (mnemonic index 1) ───────────────
DEV2_KEY = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"


# ─── Token Creation Helper ────────────────────────────────────

def create_token(w3, account, name, symbol, currency="USD",
                 gas_limit=3_000_000):
    """Create a TIP-20 token via factory. Returns checksum address."""
    import os
    salt = Web3.keccak(text=f"{name}-{os.getpid()}-{time.time()}")
    calldata = encode_create_token(name, symbol, currency, PATH_USD,
                                   account.address, salt)
    tx_hash, receipt, _ = send_tempo_tx(
        w3, account,
        calls=[Call.create(to=TIP20_FACTORY, value=0, data=calldata)],
        gas_limit=gas_limit,
    )
    if receipt["status"] != 1:
        return None
    for log in receipt.get("logs", []):
        topics = log.get("topics", [])
        if len(topics) >= 2:
            addr = "0x" + topics[1].hex()[-40:]
            candidate = Web3.to_checksum_address(addr)
            if candidate.lower().startswith("0x20c0"):
                return candidate
    return None


# ─── Additional Read Helpers ──────────────────────────────────

def read_address(w3, contract: str, func: str) -> str:
    data = _sel(f"{func}()")
    raw = call_view(w3, contract, data)
    if len(raw) == 0:
        return None
    (val,) = abi_decode(["address"], raw)
    return Web3.to_checksum_address(val)


def read_uint128(w3, contract: str, func: str) -> int:
    data = _sel(f"{func}()")
    raw = call_view(w3, contract, data)
    if len(raw) == 0:
        return 0
    (val,) = abi_decode(["uint128"], raw)
    return val


def read_bytes32(w3, contract: str, func: str) -> bytes:
    data = _sel(f"{func}()")
    raw = call_view(w3, contract, data)
    if len(raw) < 32:
        return b"\x00" * 32
    (val,) = abi_decode(["bytes32"], raw)
    return val


# ─── Additional Encoding Helpers ──────────────────────────────

def encode_set_supply_cap(cap: int) -> bytes:
    return _sel("setSupplyCap(uint256)") + abi_encode(["uint256"], [cap])


def encode_allowance(owner: str, spender: str) -> bytes:
    return _sel("allowance(address,address)") + abi_encode(
        ["address", "address"], [owner, spender])


# ─── DEX Helpers ──────────────────────────────────────────────

MAX_UINT256 = 2**256 - 1


def approve_dex(w3, account):
    """Approve DEX to spend AlphaUSD and PathUSD. Required before placing orders."""
    for token in [ALPHA_USD, PATH_USD]:
        calldata = encode_approve(STABLECOIN_DEX, MAX_UINT256)
        send_tempo_tx(w3, account,
            calls=[Call.create(to=token, value=0, data=calldata)],
            gas_limit=500_000)


# ─── DEX Encoding ─────────────────────────────────────────────

def encode_create_pair(base: str) -> bytes:
    return _sel("createPair(address)") + abi_encode(["address"], [base])


def encode_place(token: str, amount: int, is_bid: bool, tick: int) -> bytes:
    return _sel("place(address,uint128,bool,int16)") + abi_encode(
        ["address", "uint128", "bool", "int16"],
        [token, amount, is_bid, tick])


def encode_place_with_client_id(token: str, amount: int, is_bid: bool,
                                 tick: int, client_id: int) -> bytes:
    return _sel("place(address,uint128,bool,int16,uint128)") + abi_encode(
        ["address", "uint128", "bool", "int16", "uint128"],
        [token, amount, is_bid, tick, client_id])


def encode_place_flip(token: str, amount: int, is_bid: bool,
                       tick: int, flip_tick: int) -> bytes:
    return _sel("placeFlip(address,uint128,bool,int16,int16)") + abi_encode(
        ["address", "uint128", "bool", "int16", "int16"],
        [token, amount, is_bid, tick, flip_tick])


def encode_cancel_order(order_id: int) -> bytes:
    return _sel("cancel(uint128)") + abi_encode(["uint128"], [order_id])


def encode_cancel_by_client_id(client_id: int) -> bytes:
    return _sel("cancelByClientOrderId(uint128)") + abi_encode(
        ["uint128"], [client_id])


def encode_swap_exact_in(token_in: str, token_out: str,
                          amount_in: int, min_out: int) -> bytes:
    return _sel("swapExactAmountIn(address,address,uint128,uint128)") + \
        abi_encode(["address", "address", "uint128", "uint128"],
                   [token_in, token_out, amount_in, min_out])


def encode_swap_exact_out(token_in: str, token_out: str,
                           amount_out: int, max_in: int) -> bytes:
    return _sel("swapExactAmountOut(address,address,uint128,uint128)") + \
        abi_encode(["address", "address", "uint128", "uint128"],
                   [token_in, token_out, amount_out, max_in])


def encode_quote_swap_in(token_in: str, token_out: str,
                          amount_in: int) -> bytes:
    return _sel("quoteSwapExactAmountIn(address,address,uint128)") + \
        abi_encode(["address", "address", "uint128"],
                   [token_in, token_out, amount_in])


def encode_get_order(order_id: int) -> bytes:
    return _sel("getOrder(uint128)") + abi_encode(["uint128"], [order_id])


def encode_dex_pair_key(token_a: str, token_b: str) -> bytes:
    return _sel("pairKey(address,address)") + abi_encode(
        ["address", "address"], [token_a, token_b])


def encode_dex_books(pair_key: bytes) -> bytes:
    return _sel("books(bytes32)") + abi_encode(["bytes32"], [pair_key])


def encode_dex_balance(user: str, token: str) -> bytes:
    return _sel("balanceOf(address,address)") + abi_encode(
        ["address", "address"], [user, token])


def encode_dex_withdraw(token: str, amount: int) -> bytes:
    return _sel("withdraw(address,uint128)") + abi_encode(
        ["address", "uint128"], [token, amount])


def encode_next_order_id() -> bytes:
    return _sel("nextOrderId()")


def encode_get_order_by_client_id(user: str, client_id: int) -> bytes:
    return _sel("getOrderByClientOrderId(address,uint128)") + abi_encode(
        ["address", "uint128"], [user, client_id])


# ─── Permit (EIP-2612) Encoding ───────────────────────────────

def encode_permit(owner: str, spender: str, value: int, deadline: int,
                  v: int, r: bytes, s: bytes) -> bytes:
    return _sel("permit(address,address,uint256,uint256,uint8,bytes32,bytes32)") + \
        abi_encode(
            ["address", "address", "uint256", "uint256", "uint8",
             "bytes32", "bytes32"],
            [owner, spender, value, deadline, v, r, s])


def encode_nonces(owner: str) -> bytes:
    return _sel("nonces(address)") + abi_encode(["address"], [owner])


def encode_domain_separator() -> bytes:
    return _sel("DOMAIN_SEPARATOR()")


# ─── Burn Blocked Encoding ────────────────────────────────────

def encode_burn_blocked(from_addr: str, amount: int) -> bytes:
    return _sel("burnBlocked(address,uint256)") + abi_encode(
        ["address", "uint256"], [from_addr, amount])


# ─── Rewards Encoding ─────────────────────────────────────────

def encode_distribute_reward(amount: int) -> bytes:
    return _sel("distributeReward(uint256)") + abi_encode(["uint256"], [amount])


def encode_set_reward_recipient(recipient: str) -> bytes:
    return _sel("setRewardRecipient(address)") + abi_encode(
        ["address"], [recipient])


def encode_claim_rewards() -> bytes:
    return _sel("claimRewards()")


def encode_get_pending_rewards(account: str) -> bytes:
    return _sel("getPendingRewards(address)") + abi_encode(
        ["address"], [account])


def encode_opted_in_supply() -> bytes:
    return _sel("optedInSupply()")


# ─── Quote Token Encoding ─────────────────────────────────────

def encode_set_next_quote_token(token: str) -> bytes:
    return _sel("setNextQuoteToken(address)") + abi_encode(
        ["address"], [token])


def encode_complete_quote_token_update() -> bytes:
    return _sel("completeQuoteTokenUpdate()")


# ─── Compound Policy Encoding ─────────────────────────────────

def encode_create_compound_policy(sender_id: int, recipient_id: int,
                                   mint_recipient_id: int) -> bytes:
    return _sel("createCompoundPolicy(uint64,uint64,uint64)") + abi_encode(
        ["uint64", "uint64", "uint64"],
        [sender_id, recipient_id, mint_recipient_id])


def encode_compound_policy_data(policy_id: int) -> bytes:
    return _sel("compoundPolicyData(uint64)") + abi_encode(
        ["uint64"], [policy_id])


def encode_is_authorized_sender(policy_id: int, user: str) -> bytes:
    return _sel("isAuthorizedSender(uint64,address)") + abi_encode(
        ["uint64", "address"], [policy_id, user])


def encode_is_authorized_recipient(policy_id: int, user: str) -> bytes:
    return _sel("isAuthorizedRecipient(uint64,address)") + abi_encode(
        ["uint64", "address"], [policy_id, user])


def encode_modify_blacklist(policy_id: int, account: str,
                             restricted: bool) -> bytes:
    return _sel("modifyPolicyBlacklist(uint64,address,bool)") + abi_encode(
        ["uint64", "address", "bool"], [policy_id, account, restricted])


# ─── Fee Manager Advanced ─────────────────────────────────────

def encode_burn_liquidity(user_token: str, validator_token: str,
                           liquidity: int, to: str) -> bytes:
    return _sel("burn(address,address,uint256,address)") + abi_encode(
        ["address", "address", "uint256", "address"],
        [user_token, validator_token, liquidity, to])


def encode_get_pool(user_token: str, validator_token: str) -> bytes:
    return _sel("getPool(address,address)") + abi_encode(
        ["address", "address"], [user_token, validator_token])


def encode_get_pool_id(user_token: str, validator_token: str) -> bytes:
    return _sel("getPoolId(address,address)") + abi_encode(
        ["address", "address"], [user_token, validator_token])


def encode_pool_total_supply(pool_id: bytes) -> bytes:
    return _sel("totalSupply(bytes32)") + abi_encode(["bytes32"], [pool_id])


def encode_liquidity_balances(pool_id: bytes, user: str) -> bytes:
    return _sel("liquidityBalances(bytes32,address)") + abi_encode(
        ["bytes32", "address"], [pool_id, user])


def encode_collected_fees(validator: str, token: str) -> bytes:
    return _sel("collectedFees(address,address)") + abi_encode(
        ["address", "address"], [validator, token])


# ─── Keychain Advanced ────────────────────────────────────────

def encode_update_spending_limit(key_id: str, token: str,
                                  new_limit: int) -> bytes:
    return _sel("updateSpendingLimit(address,address,uint256)") + abi_encode(
        ["address", "address", "uint256"], [key_id, token, new_limit])


# ─── TIP-20 Policy Integration ───────────────────────────────

def encode_change_transfer_policy_id(policy_id: int) -> bytes:
    return _sel("changeTransferPolicyId(uint64)") + abi_encode(
        ["uint64"], [policy_id])


def encode_transfer_policy_id() -> bytes:
    return _sel("transferPolicyId()")


# ─── TIP-403 Compound (TIP-1015) Additional ──────────────────

def encode_is_authorized_mint_recipient(policy_id: int, user: str) -> bytes:
    return _sel("isAuthorizedMintRecipient(uint64,address)") + abi_encode(
        ["uint64", "address"], [policy_id, user])


def encode_policy_exists(policy_id: int) -> bytes:
    return _sel("policyExists(uint64)") + abi_encode(["uint64"], [policy_id])
