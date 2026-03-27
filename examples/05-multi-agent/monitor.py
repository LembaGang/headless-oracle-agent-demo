"""
Example 05 — Multi-exchange parallel batch check.

Before executing a global trade strategy, verify all required exchanges are OPEN.
A single HALTED or UNKNOWN exchange is enough to abort — fail-closed.

pip install requests
export HEADLESS_ORACLE_API_KEY=your_key

Run: python monitor.py
     EXCHANGES=XNYS,XLON,XJPX python monitor.py
"""
import json
import os
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

ORACLE_BASE = "https://api.headlessoracle.com"
KEY = os.environ.get("HEADLESS_ORACLE_API_KEY", "")

# Default: check the three largest exchanges across time zones
EXCHANGES = os.environ.get("EXCHANGES", "XNYS,XLON,XJPX").split(",")

STATUS_ICON = {"OPEN": "🟢", "CLOSED": "⚫", "HALTED": "🔴", "UNKNOWN": "🟠"}


def check_one(mic: str) -> dict:
    """Fetch market status for a single exchange. Fail-closed on error."""
    endpoint = "status" if KEY else "demo"
    url = f"{ORACLE_BASE}/v5/{endpoint}?mic={mic}"
    req = urllib.request.Request(url, headers={"X-Oracle-Key": KEY} if KEY else {})
    try:
        data = json.loads(urllib.request.urlopen(req, timeout=10).read())
        return {
            "mic": mic,
            "status": data.get("status", "UNKNOWN"),
            "receipt_id": data.get("receipt_id", "—"),
            "expires_at": data.get("expires_at", "—"),
        }
    except Exception as e:
        return {"mic": mic, "status": "UNKNOWN", "error": str(e)}


def main():
    print(f"\n{'═' * 60}")
    print(f"  Global Market Safety Check — {len(EXCHANGES)} exchanges")
    print(f"  Checking: {', '.join(EXCHANGES)}")
    print(f"{'═' * 60}\n")

    # Parallel fetch — all exchanges simultaneously
    results = {}
    with ThreadPoolExecutor(max_workers=len(EXCHANGES)) as pool:
        futures = {pool.submit(check_one, mic): mic for mic in EXCHANGES}
        for future in as_completed(futures):
            r = future.result()
            results[r["mic"]] = r

    # Print results in original order
    print(f"  {'Exchange':<8}  {'Status':<10}  Receipt ID")
    print(f"  {'─' * 8}  {'─' * 10}  {'─' * 36}")
    for mic in EXCHANGES:
        r = results[mic]
        status = r["status"]
        icon = STATUS_ICON.get(status, "❓")
        rid = r.get("receipt_id", "—")[:16]
        print(f"  {mic:<8}  {icon} {status:<8}  {rid}…")

    # Global safety decision
    statuses = {r["status"] for r in results.values()}
    all_open = statuses == {"OPEN"}
    any_unsafe = bool(statuses & {"HALTED", "UNKNOWN"})

    print(f"\n{'─' * 60}")

    if any_unsafe:
        unsafe = [mic for mic, r in results.items() if r["status"] in ("HALTED", "UNKNOWN")]
        print(f"🛑 ABORT: {', '.join(unsafe)} {'are' if len(unsafe) > 1 else 'is'} HALTED/UNKNOWN.")
        print("   Fail-closed: do not execute any cross-exchange trades.")
        sys.exit(1)

    if not all_open:
        closed = [mic for mic, r in results.items() if r["status"] == "CLOSED"]
        print(f"⏸️  WAIT: {', '.join(closed)} {'are' if len(closed) > 1 else 'is'} CLOSED.")
        print("   All exchanges must be OPEN for global strategy execution.")
        sys.exit(0)

    print("✅ ALL exchanges are OPEN — safe to execute global strategy.\n")


if __name__ == "__main__":
    main()
