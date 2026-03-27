"""
Example 03 — LangChain trading agent with market safety gate.

The agent MUST verify market state before any trade decision.
UNKNOWN and HALTED are treated as CLOSED (fail-closed).

pip install headless-oracle-langchain langchain-openai
export OPENAI_API_KEY=...
# HEADLESS_ORACLE_API_KEY is auto-provisioned on first run if not set

Run: python agent.py
"""
import os
from headless_oracle_langchain import MarketStatusTool, MarketScheduleTool
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate

# ── Tools ─────────────────────────────────────────────────────────────────────
tools = [MarketStatusTool(), MarketScheduleTool()]

# ── System prompt enforcing fail-closed behaviour ─────────────────────────────
SYSTEM_PROMPT = """You are a market-safe trading assistant. You have access to a
cryptographically signed market oracle (Headless Oracle).

MANDATORY RULES — never break these:
1. Before discussing any trade, ALWAYS call headless_oracle_market_status first.
2. If status is OPEN: proceed with analysis.
3. If status is CLOSED, HALTED, or UNKNOWN: immediately respond
   "Market is {status}. Cannot proceed with trade execution. Will retry at next open."
4. Never recommend trade execution without a verified OPEN receipt in this conversation.
5. HALTED means a circuit breaker is active — this is more serious than CLOSED.
   Treat it identically to UNKNOWN: halt all execution, no exceptions.

Note: The oracle returns Signed Market Attestations (SMA). SMA = Signed Market Attestation,
not Simple Moving Average. The signature is Ed25519 and can be independently verified."""

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

# ── Agent ─────────────────────────────────────────────────────────────────────
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
agent = create_tool_calling_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# ── Run ───────────────────────────────────────────────────────────────────────
query = os.environ.get(
    "QUERY",
    "Should I execute a buy order for AAPL right now? I want to buy 100 shares on NYSE."
)

print(f"\nQuery: {query}\n{'─' * 60}")
result = executor.invoke({"input": query})
print(f"\n{'─' * 60}\nAnswer: {result['output']}")
