/**
 * Example 01 — Basic market status query (TypeScript).
 *
 * npx tsx query.ts
 * MIC=XLON npx tsx query.ts
 */

const MIC = process.env.MIC ?? 'XNYS';
const KEY = process.env.HEADLESS_ORACLE_API_KEY ?? '';

const url = `https://api.headlessoracle.com/v5/${KEY ? 'status' : 'demo'}?mic=${MIC}`;
const res = await fetch(url, KEY ? { headers: { 'X-Oracle-Key': KEY } } : {});
const receipt = await res.json();

const status: string = receipt.status ?? 'UNKNOWN';

console.log(`${MIC}: ${status}`);
console.log(`Receipt ID : ${receipt.receipt_id ?? '—'}`);
console.log(`Expires at : ${receipt.expires_at ?? '—'}`);
console.log(`Signature  : ${(receipt.signature ?? '—').slice(0, 32)}…`);

// Fail-closed: UNKNOWN and HALTED must be treated as CLOSED
if (['UNKNOWN', 'HALTED', 'CLOSED'].includes(status)) {
  console.log('\n⛔ Market is not OPEN — do not execute trades.');
  process.exit(1);
}

console.log('\n✅ Market is OPEN — safe to proceed.');
