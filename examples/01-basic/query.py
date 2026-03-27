"""
Example 01 — Basic market status query.

pip install headless-oracle-langchain  # optional: for auto-provisioning
# or just set: export HEADLESS_ORACLE_API_KEY=your_key

Run: python query.py
"""
import json, os, urllib.request

MIC = os.environ.get("MIC", "XNYS")           # exchange to check
KEY = os.environ.get("HEADLESS_ORACLE_API_KEY", "")

url = f"https://api.headlessoracle.com/v5/{'status' if KEY else 'demo'}?mic={MIC}"
req = urllib.request.Request(url, headers={"X-Oracle-Key": KEY} if KEY else {})
receipt = json.loads(urllib.request.urlopen(req, timeout=10).read())

status = receipt.get("status", "UNKNOWN")

print(f"{MIC}: {status}")
print(f"Receipt ID : {receipt.get('receipt_id', '—')}")
print(f"Expires at : {receipt.get('expires_at', '—')}")
print(f"Signature  : {receipt.get('signature', '—')[:32]}…")

# Fail-closed: UNKNOWN and HALTED must be treated as CLOSED
if status in ("UNKNOWN", "HALTED", "CLOSED"):
    print("\n⛔ Market is not OPEN — do not execute trades.")
    raise SystemExit(1)

print("\n✅ Market is OPEN — safe to proceed.")
