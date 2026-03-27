<p align="center">
  <img src="https://headlessoracle.com/logo.png" alt="Headless Oracle" width="80" />
</p>

<h2 align="center">Headless Oracle Agent Demo</h2>

<p align="center"><strong>Before your agent trades, it needs to know the market is open.</strong></p>

<p align="center">
  <a href="https://github.com/marketplace/actions/headless-oracle-market-safety-check"><img src="https://img.shields.io/badge/GitHub_Action-Market_Safety_Check-2ea44f?logo=github" alt="GitHub Action" /></a>
  <a href="https://pypi.org/project/headless-oracle-langchain/"><img src="https://img.shields.io/pypi/v/headless-oracle-langchain?label=LangChain" alt="PyPI LangChain" /></a>
  <a href="https://pypi.org/project/headless-oracle-crewai/"><img src="https://img.shields.io/pypi/v/headless-oracle-crewai?label=CrewAI" alt="PyPI CrewAI" /></a>
  <a href="https://www.npmjs.com/package/@headlessoracle/verify"><img src="https://img.shields.io/npm/v/@headlessoracle/verify?label=%40headlessoracle%2Fverify" alt="npm" /></a>
  <a href="https://headlessoracle.com/v5/compliance"><img src="https://img.shields.io/badge/APTS-6%2F6_checks-brightgreen" alt="APTS Compliant" /></a>
  <a href="https://headlessoracle.com/docs/x402-payments"><img src="https://img.shields.io/badge/x402-autonomous_payments-7c3aed" alt="x402 Enabled" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow" alt="MIT License" /></a>
</p>

<p align="center">
  <!-- HUMAN TASK: Record a 30-second GIF showing examples/04-x402-autopay/agent.py running:
       terminal shows agent paying 0.001 USDC → minting key → querying oracle → OPEN receipt
       Save as docs/demo.gif and uncomment the line below. -->
  <!-- <img src="docs/demo.gif" alt="Agent autonomously pays for market data" width="700" /> -->
</p>

---

This repo demonstrates **Headless Oracle** — a cryptographically signed market state oracle for autonomous AI agents. It's also:

- **The first finance GitHub Action on the marketplace** — add a market safety check to any workflow in 3 lines
- **A live proof of the x402 "agent pays itself" pattern** — the agent holds a Base mainnet wallet and pays for its own API access in USDC, with no human in the loop
- **A progressive 5-example onramp** for every major agent framework (LangChain, CrewAI, raw HTTP)

Receipts are [Ed25519-signed](https://headlessoracle.com/docs/sma-protocol/rfc-001), portable bearer attestations — one agent can verify another agent's receipt without calling the API again. 28 global exchanges. Fail-closed: `UNKNOWN` and `HALTED` are always treated as `CLOSED`.

---

## Quickstart — under 2 minutes

**Option A: Python (no install required)**
```bash
# Check if NYSE is open right now
python examples/01-basic/query.py
```

**Option B: curl**
```bash
curl "https://api.headlessoracle.com/v5/demo?mic=XNYS" | python3 -m json.tool
```

**Option C: GitHub Action (add to any workflow)**
```yaml
- uses: LembaGang/headless-oracle-agent-demo@v1
  with:
    mic: XNYS               # NYSE — or XLON, XJPX, XCOI, any of 28 exchanges
    allow_closed: false     # fail if market is CLOSED
```

**Option D: LangChain / CrewAI**
```bash
pip install headless-oracle-langchain   # or headless-oracle-crewai
```
```python
from headless_oracle_langchain import MarketStatusTool
tools = [MarketStatusTool()]  # auto-provisions a free sandbox key on first call
```

---

## The GitHub Action — first finance Action in the marketplace

```yaml
# .github/workflows/trading.yml
- name: Verify NYSE is open
  id: oracle
  uses: LembaGang/headless-oracle-agent-demo@v1
  with:
    mic: XNYS
    allow_closed: false
    api_key: ${{ secrets.HEADLESS_ORACLE_API_KEY }}  # optional

# Access outputs in later steps
- run: echo "Status: ${{ steps.oracle.outputs.status }}"
```

**What happens:**
- ✅ `OPEN` → workflow continues
- ⏸️ `CLOSED` → fails if `allow_closed: false`, continues if `true` (default)
- 🛑 `HALTED` → **always fails** (circuit breaker active — fail-closed)
- ⚠️ `UNKNOWN` → **always fails** (oracle couldn't determine state — fail-closed)

**Outputs:** `status`, `safe_to_execute`, `receipt_id`, `expires_at`, `signature`

Each run writes a [Step Summary](https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/adding-a-job-summary) with the full signed receipt and a link to verify it independently.

**Why this doesn't exist anywhere else:**

The GitHub Actions Marketplace has no finance, trading, or market data Actions. This is the first. The fail-closed design means the action makes the safe choice automatically — your CI doesn't need to know what "HALTED" means; the action handles it.

---

## x402: The agent that pays for itself

[`examples/04-x402-autopay/agent.py`](examples/04-x402-autopay/agent.py) demonstrates an autonomous agent that funds its own API access using the [x402 protocol](https://headlessoracle.com/docs/x402-payments):

```
Agent starts → no API key found → checks Base wallet balance →
sends 0.001 USDC → tx confirmed in ~2s → /v5/x402/mint →
persistent ho_live_ key (50K calls/day) → calls Oracle → OPEN receipt
```

No human in the loop. The agent is the economic actor.

```bash
# Requires a Base mainnet wallet with ~0.001 USDC + ~0.001 ETH for gas
pip install web3 requests
export AGENT_WALLET_PRIVATE_KEY=0x...

python examples/04-x402-autopay/agent.py
```

The key resolution order (implemented in all examples):

| Priority | Source | Best for |
|----------|--------|----------|
| 1 | `HEADLESS_ORACLE_API_KEY` env var | containers, CI/CD, serverless |
| 2 | `~/.headless_oracle/config.json` | local development |
| 3 | x402 autonomous payment (Base USDC) | self-funding agents |
| 4 | sandbox auto-provision (100 calls/day) | zero-config first run |

---

## All 5 examples

| # | Example | What it shows | Run |
|---|---------|---------------|-----|
| 01 | [Basic query](examples/01-basic/) | Fetch a signed receipt — Python + TypeScript | `python examples/01-basic/query.py` |
| 02 | [Verify receipt](examples/02-verify/) | Ed25519 signature verification | `npx tsx examples/02-verify/verify.ts` |
| 03 | [LangChain agent](examples/03-langchain/) | Fail-closed trading agent with system prompt | `python examples/03-langchain/agent.py` |
| 04 | [x402 autopay](examples/04-x402-autopay/) | **Agent pays for its own key using Base USDC** | `python examples/04-x402-autopay/agent.py` |
| 05 | [Multi-exchange](examples/05-multi-agent/) | Parallel check across all required exchanges | `python examples/05-multi-agent/monitor.py` |

---

## How it works

Every Oracle response is a **Signed Market Attestation (SMA)** — a cryptographic receipt:

```json
{
  "mic": "XNYS",
  "status": "OPEN",
  "issued_at": "2026-03-27T14:31:00Z",
  "expires_at": "2026-03-27T14:32:00Z",
  "receipt_mode": "live",
  "issuer": "headlessoracle.com",
  "receipt_id": "f3a2b1c0-...",
  "signature": "a3f2e1d0c9b8...",
  "discovery_url": "https://headlessoracle.com/.well-known/mcp/server-card.json"
}
```

> **SMA = Signed Market Attestation** — not Simple Moving Average.

- **Ed25519 signed** — verify with [`@headlessoracle/verify`](https://npmjs.com/package/@headlessoracle/verify) or the Web Crypto API
- **60-second TTL** — `expires_at` prevents stale receipts from being acted on
- **Portable** — pass between agents; downstream agent verifies without calling the API again
- **Fail-closed** — `UNKNOWN` and `HALTED` are always treated as `CLOSED`

Verify any receipt independently:
```bash
npm install @headlessoracle/verify
```
```js
import { verify } from '@headlessoracle/verify';
const result = await verify(receipt);
// { valid: true, expired: false, reason: null }
```

Public key registry: [`headlessoracle.com/.well-known/oracle-keys.json`](https://headlessoracle.com/.well-known/oracle-keys.json)

---

## 28 exchanges, DST-aware, fail-closed

| Region | Exchanges |
|--------|-----------|
| Americas | XNYS (NYSE), XNAS (NASDAQ), XBSP (Brazil B3) |
| Europe | XLON (LSE), XPAR (Paris), XSWX (Swiss), XMIL (Milan), XHEL (Helsinki), XSTO (Stockholm) |
| Middle East & Africa | XSAU (Riyadh), XDFM (Dubai), XJSE (Johannesburg) |
| Asia-Pacific | XJPX (Tokyo), XHKG (Hong Kong), XSHG (Shanghai), XSHE (Shenzhen), XKRX (Seoul), XBOM (BSE India), XNSE (NSE India), XSES (Singapore), XASX (Sydney), XNZE (Auckland) |
| Derivatives | XCBT (CME overnight), XNYM (NYMEX overnight), XCBO (Cboe) |
| Crypto (24/7) | XCOI (Coinbase), XBIN (Binance) |

DST transitions are handled automatically via IANA timezone identifiers. No hardcoded UTC offsets. Check [`/v5/dst-risk`](https://api.headlessoracle.com/v5/dst-risk) before each seasonal transition.

---

## Use as an MCP server (Claude Desktop, Cursor, Windsurf)

```bash
npx headless-oracle-setup
```

Or add to your MCP config manually:
```json
{
  "mcpServers": {
    "headless-oracle": {
      "url": "https://headlessoracle.com/mcp"
    }
  }
}
```

Tools: `get_market_status`, `get_market_schedule`, `list_exchanges`, `verify_receipt`

---

## Links

- [Docs](https://headlessoracle.com/docs)
- [SMA Protocol RFC-001](https://headlessoracle.com/docs/sma-protocol/rfc-001) — the open standard this implements
- [Agent Pre-Trade Safety Standard (APTS)](https://github.com/LembaGang/agent-pretrade-safety-standard) — 6-check compliance checklist
- [x402 Payments Guide](https://headlessoracle.com/docs/x402-payments)
- [Live status: all 28 exchanges](https://headlessoracle.com/status)
- [OpenAPI spec](https://headlessoracle.com/openapi.json)
- [Conformance vectors](https://api.headlessoracle.com/v5/conformance-vectors) — test your SDK against live-signed receipts

---

## License

MIT — see [LICENSE](LICENSE)

The SMA Protocol specification is Apache 2.0 — see [LembaGang/sma-protocol](https://github.com/LembaGang/sma-protocol)
