"""
Example 04 — Autonomous agent that pays for its own Oracle access via x402.

This agent starts with zero configuration. If no API key is found, it pays
0.001 USDC from its own Base mainnet wallet, mints a persistent key, and
proceeds. No human intervention required.

This is the "agent pays itself" pattern — the agent is the economic actor.

Prerequisites:
  pip install web3 requests
  export AGENT_WALLET_PRIVATE_KEY=0x...   # Base mainnet wallet with ~$0.01 USDC
  export MIC=XNYS                          # optional, default XNYS

The agent wallet needs:
  - ~0.001 USDC for the Oracle key payment (Base mainnet)
  - ~0.001 ETH for gas (Base is very cheap — ~$0.001/tx)

Get Base USDC: bridge.base.org or Coinbase → Base mainnet
Oracle payment address: 0x26D4Ffe98017D2f160E2dAaE9d119e3d8b860AD3
Oracle docs: https://headlessoracle.com/docs/x402-payments

Run: python agent.py
"""
import json
import os
import sys
import time
from pathlib import Path

import requests

# ── Constants ─────────────────────────────────────────────────────────────────
ORACLE_BASE = "https://api.headlessoracle.com"
ORACLE_PAYMENT_ADDRESS = "0x26D4Ffe98017D2f160E2dAaE9d119e3d8b860AD3"
USDC_CONTRACT = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"  # USDC on Base mainnet
BASE_RPC = "https://mainnet.base.org"
BASE_CHAIN_ID = 8453
USDC_AMOUNT = 1000  # 0.001 USDC (6 decimals = 1000 units)
CONFIG_PATH = Path.home() / ".headless_oracle" / "config.json"


# ── Step 1: Resolve API key ───────────────────────────────────────────────────

def resolve_api_key() -> tuple[str, str]:
    """
    Key resolution order:
    (1) HEADLESS_ORACLE_API_KEY env var
    (2) ~/.headless_oracle/config.json
    (3) x402 autonomous payment (requires AGENT_WALLET_PRIVATE_KEY)
    (4) sandbox auto-provision (100 calls/day, no wallet needed)

    Returns (key, source) where source describes how the key was obtained.
    """
    # (1) Env var — preferred for containers and CI
    key = os.environ.get("HEADLESS_ORACLE_API_KEY", "")
    if key:
        return key, "env"

    # (2) Config file — set by previous auto-provision or manual setup
    if CONFIG_PATH.exists():
        try:
            config = json.loads(CONFIG_PATH.read_text())
            key = config.get("api_key", "")
            if key:
                return key, "config_file"
        except Exception:
            pass

    # (3) x402 autonomous payment — agent pays for its own persistent key
    wallet_key = os.environ.get("AGENT_WALLET_PRIVATE_KEY", "")
    if wallet_key:
        print("🤖 No API key found. Agent is paying for access via x402…")
        key = x402_mint_key(wallet_key)
        if key:
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            CONFIG_PATH.write_text(json.dumps({"api_key": key}))
            print(f"✅ Key minted and saved to {CONFIG_PATH}")
            return key, "x402_autonomous"

    # (4) Sandbox auto-provision — free, rate-limited, no wallet needed
    print("📦 Provisioning free sandbox key (100 calls/24h)…")
    try:
        resp = requests.get(f"{ORACLE_BASE}/v5/sandbox", timeout=10)
        resp.raise_for_status()
        key = resp.json().get("api_key", "")
        if key:
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            CONFIG_PATH.write_text(json.dumps({"api_key": key}))
            return key, "sandbox_provisioned"
    except Exception as e:
        print(f"⚠️  Sandbox provision failed: {e}")

    return "", "none"


# ── Step 2: x402 payment flow ─────────────────────────────────────────────────

def x402_mint_key(private_key: str) -> str:
    """
    Send 0.001 USDC on Base mainnet to the Oracle payment address,
    then call /v5/x402/mint to get a persistent API key.

    The minted key is a builder-tier key (50K calls/day) that never expires.
    """
    try:
        from web3 import Web3
        from eth_account import Account
    except ImportError:
        print("⚠️  web3 not installed. Run: pip install web3")
        return ""

    w3 = Web3(Web3.HTTPProvider(BASE_RPC))
    if not w3.is_connected():
        print(f"⚠️  Cannot connect to Base RPC ({BASE_RPC})")
        return ""

    account = Account.from_key(private_key)
    print(f"   Agent wallet: {account.address}")

    # Check USDC balance
    usdc_abi = [
        {"inputs": [{"type": "address"}], "name": "balanceOf",
         "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
        {"inputs": [{"type": "address"}, {"type": "uint256"}], "name": "transfer",
         "outputs": [{"type": "bool"}], "stateMutability": "nonpayable", "type": "function"},
    ]
    usdc = w3.eth.contract(
        address=Web3.to_checksum_address(USDC_CONTRACT),
        abi=usdc_abi,
    )
    balance = usdc.functions.balanceOf(account.address).call()
    print(f"   USDC balance: {balance / 1_000_000:.4f} USDC")

    if balance < USDC_AMOUNT:
        print(f"⚠️  Insufficient USDC. Need {USDC_AMOUNT / 1_000_000} USDC, have {balance / 1_000_000:.4f} USDC")
        print(f"   Bridge USDC to Base: https://bridge.base.org")
        return ""

    # Build and send the USDC transfer
    print(f"   Sending {USDC_AMOUNT / 1_000_000} USDC → {ORACLE_PAYMENT_ADDRESS}…")
    tx = usdc.functions.transfer(
        Web3.to_checksum_address(ORACLE_PAYMENT_ADDRESS),
        USDC_AMOUNT,
    ).build_transaction({
        "from": account.address,
        "nonce": w3.eth.get_transaction_count(account.address),
        "chainId": BASE_CHAIN_ID,
    })

    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    tx_hash_hex = "0x" + tx_hash.hex()
    print(f"   Transaction: {tx_hash_hex}")
    print(f"   Basescan: https://basescan.org/tx/{tx_hash_hex}")

    # Wait for confirmation (Base finalises in ~2s)
    print("   Waiting for confirmation…")
    receipt = None
    for _ in range(30):  # 30s timeout
        try:
            receipt = w3.eth.get_transaction_receipt(tx_hash)
            if receipt:
                break
        except Exception:
            pass
        time.sleep(1)

    if not receipt or receipt.status != 1:
        print("⚠️  Transaction failed or timed out.")
        return ""

    print(f"   ✅ Confirmed in block {receipt.blockNumber}")

    # Mint the Oracle API key
    print("   Calling /v5/x402/mint…")
    try:
        mint_resp = requests.post(
            f"{ORACLE_BASE}/v5/x402/mint",
            json={"tx_hash": tx_hash_hex},
            timeout=30,
        )
        mint_resp.raise_for_status()
        data = mint_resp.json()
        api_key = data.get("api_key", "")
        plan = data.get("plan", "unknown")
        daily_limit = data.get("daily_limit", "unknown")
        print(f"   ✅ Key minted — plan: {plan}, limit: {daily_limit} calls/day")
        return api_key
    except Exception as e:
        print(f"⚠️  Mint failed: {e}")
        return ""


# ── Step 3: Query the Oracle ───────────────────────────────────────────────────

def check_market(mic: str, api_key: str) -> dict:
    """Fetch a signed market status receipt. Fail-closed on any error."""
    endpoint = "status" if api_key else "demo"
    url = f"{ORACLE_BASE}/v5/{endpoint}?mic={mic}"
    headers = {"X-Oracle-Key": api_key} if api_key else {}

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        # Fail-closed: if Oracle is unreachable, treat as UNKNOWN
        return {"status": "UNKNOWN", "error": str(e)}


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    mic = os.environ.get("MIC", "XNYS")
    print(f"\n{'═' * 60}")
    print(f"  Headless Oracle — Autonomous Agent Demo")
    print(f"  Exchange: {mic}")
    print(f"{'═' * 60}\n")

    # Resolve key (agent handles its own authentication)
    api_key, source = resolve_api_key()
    print(f"\n🔑 API key source: {source or 'none (using demo endpoint)'}\n")

    # Check market state
    print(f"📡 Fetching market status for {mic}…")
    receipt = check_market(mic, api_key)

    status = receipt.get("status", "UNKNOWN")
    receipt_id = receipt.get("receipt_id", "—")
    expires_at = receipt.get("expires_at", "—")
    signature = receipt.get("signature", "")
    receipt_mode = receipt.get("receipt_mode", "—")

    print(f"\n{'─' * 60}")
    print(f"  Status       : {status}")
    print(f"  Receipt mode : {receipt_mode}")
    print(f"  Receipt ID   : {receipt_id}")
    print(f"  Expires at   : {expires_at}")
    if signature:
        print(f"  Signature    : {signature[:32]}…")
    print(f"{'─' * 60}\n")

    # Fail-closed decision logic
    if status == "OPEN":
        print(f"✅ {mic} is OPEN — safe to execute trades.\n")
    elif status == "CLOSED":
        print(f"⏸️  {mic} is CLOSED — outside trading hours.")
        print(f"   Next session: {ORACLE_BASE}/v5/schedule?mic={mic}\n")
        sys.exit(0)  # CLOSED is expected — not an error
    elif status == "HALTED":
        print(f"🛑 {mic} is HALTED (circuit breaker active).")
        print(f"   Treat as CLOSED. Do not execute trades.\n")
        sys.exit(1)
    else:  # UNKNOWN
        print(f"⚠️  {mic} state is UNKNOWN.")
        print(f"   Treat as CLOSED per fail-closed policy. Do not execute trades.\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
