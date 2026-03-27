/**
 * Example 02 — Cryptographic receipt verification.
 *
 * Receipts are portable bearer attestations — any downstream agent or system
 * can verify them independently without calling the Oracle again.
 *
 * npm install @headlessoracle/verify
 * npx tsx verify.ts
 */

import { verify } from '@headlessoracle/verify';

const MIC = process.env.MIC ?? 'XNYS';
const KEY = process.env.HEADLESS_ORACLE_API_KEY ?? '';

// ── 1. Fetch a receipt ────────────────────────────────────────────────────────
const url = `https://api.headlessoracle.com/v5/${KEY ? 'status' : 'demo'}?mic=${MIC}`;
const res = await fetch(url, KEY ? { headers: { 'X-Oracle-Key': KEY } } : {});
const wrapper = await res.json();

// The receipt fields are at the top level (discovery_url wrapper).
// The nested .receipt contains the same signed payload.
const receipt = wrapper.receipt ?? wrapper;

console.log('── Raw receipt ──────────────────────────────');
console.log(JSON.stringify(receipt, null, 2));

// ── 2. Verify the Ed25519 signature ──────────────────────────────────────────
const result = await verify(receipt);

console.log('\n── Verification result ──────────────────────');
console.log(`valid    : ${result.valid}`);
console.log(`expired  : ${result.expired}`);
console.log(`reason   : ${result.reason ?? '—'}`);

if (!result.valid) {
  console.error('\n❌ Receipt is INVALID — do not act on this status.');
  process.exit(1);
}

if (result.expired) {
  console.warn('\n⚠️  Receipt is EXPIRED — fetch a fresh one before acting.');
  process.exit(1);
}

const status = receipt.status ?? 'UNKNOWN';
console.log(`\n✅ Verified: ${MIC} is ${status}`);

// Fail-closed
if (['UNKNOWN', 'HALTED', 'CLOSED'].includes(status)) {
  console.log('⛔ Market is not OPEN — do not execute trades.');
  process.exit(1);
}

console.log('✅ Market is OPEN and receipt is valid — safe to proceed.');
