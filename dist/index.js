#!/usr/bin/env node
/**
 * Headless Oracle — Market Safety Check GitHub Action
 * Pure Node.js 24, zero npm dependencies.
 * Uses native fetch (Node 18+) and GitHub Actions environment protocol.
 */

'use strict';

// ── Minimal Actions protocol (no @actions/core dependency) ──────────────────

function getInput(name) {
  const key = `INPUT_${name.toUpperCase().replace(/ /g, '_')}`;
  return (process.env[key] || '').trim();
}

function setOutput(name, value) {
  const filePath = process.env.GITHUB_OUTPUT;
  if (filePath) {
    const fs = require('fs');
    fs.appendFileSync(filePath, `${name}=${value}\n`);
  } else {
    // Fallback for older runners
    process.stdout.write(`::set-output name=${name}::${value}\n`);
  }
}

function info(msg) {
  console.log(msg);
}

function warning(msg) {
  process.stdout.write(`::warning::${msg}\n`);
}

function setFailed(msg) {
  process.stdout.write(`::error::${msg}\n`);
  process.exitCode = 1;
}

async function writeSummary(mic, status, receipt) {
  const summaryFile = process.env.GITHUB_STEP_SUMMARY;
  if (!summaryFile) return;
  const fs = require('fs');

  const statusEmoji = { OPEN: '🟢', CLOSED: '⚫', HALTED: '🔴', UNKNOWN: '🟠' };
  const emoji = statusEmoji[status] || '❓';

  const issuedAt = receipt.issued_at || receipt.receipt?.issued_at || '—';
  const expiresAt = receipt.expires_at || receipt.receipt?.expires_at || '—';
  const receiptId = receipt.receipt_id || receipt.receipt?.receipt_id || '—';
  const source = receipt.source || receipt.receipt?.source || '—';
  const receiptMode = receipt.receipt_mode || receipt.receipt?.receipt_mode || '—';

  const summary = [
    `## ${emoji} Market Safety Check — ${mic}`,
    '',
    `| Field | Value |`,
    `|-------|-------|`,
    `| **Status** | \`${status}\` |`,
    `| Exchange | ${mic} |`,
    `| Receipt Mode | ${receiptMode} |`,
    `| Source | ${source} |`,
    `| Issued At | ${issuedAt} |`,
    `| Expires At | ${expiresAt} |`,
    `| Receipt ID | \`${receiptId}\` |`,
    '',
    status === 'OPEN'
      ? '✅ **Market is OPEN** — safe to proceed with execution.'
      : status === 'CLOSED'
      ? '⏸️ **Market is CLOSED** — outside trading hours.'
      : status === 'HALTED'
      ? '🛑 **Market is HALTED** — circuit breaker active. Workflow failed (fail-closed).'
      : '⚠️ **Market state UNKNOWN** — oracle could not determine status. Workflow failed (fail-closed).',
    '',
    `> Verify this receipt independently: [headlessoracle.com/docs](https://headlessoracle.com/docs) | [SMA Protocol RFC-001](https://headlessoracle.com/docs/sma-protocol/rfc-001)`,
  ].join('\n');

  fs.appendFileSync(summaryFile, summary + '\n');
}

// ── Main ─────────────────────────────────────────────────────────────────────

async function run() {
  const mic = getInput('mic') || 'XNYS';
  const allowClosed = getInput('allow_closed') !== 'false';
  const apiKey = getInput('api_key') || '';

  // Validate MIC format (basic check — server validates fully)
  if (!/^[A-Z]{4}$/.test(mic)) {
    setFailed(`Invalid MIC code: "${mic}". Must be 4 uppercase letters (e.g. XNYS, XLON, XJPX).`);
    return;
  }

  const url = apiKey
    ? `https://api.headlessoracle.com/v5/status?mic=${mic}`
    : `https://api.headlessoracle.com/v5/demo?mic=${mic}`;

  const headers = {};
  if (apiKey) headers['X-Oracle-Key'] = apiKey;

  info(`Checking market status for ${mic}…`);

  let receipt;
  try {
    const res = await fetch(url, { headers });
    if (!res.ok && res.status !== 402) {
      const body = await res.text();
      setFailed(`Oracle returned HTTP ${res.status}: ${body.slice(0, 200)}`);
      return;
    }
    receipt = await res.json();
  } catch (err) {
    // Network failure — fail closed (treat as UNKNOWN)
    setFailed(`Oracle unreachable: ${err.message}. Treating as UNKNOWN (fail-closed).`);
    return;
  }

  // The discovery_url wrapper puts receipt fields at top level + nested .receipt
  const status = receipt.status || receipt.receipt?.status || 'UNKNOWN';
  const safeToExecute = status === 'OPEN';
  const receiptId = receipt.receipt_id || receipt.receipt?.receipt_id || '';
  const expiresAt = receipt.expires_at || receipt.receipt?.expires_at || '';
  const signature = receipt.signature || receipt.receipt?.signature || '';

  setOutput('status', status);
  setOutput('safe_to_execute', String(safeToExecute));
  setOutput('receipt_id', receiptId);
  setOutput('expires_at', expiresAt);
  setOutput('signature', signature);

  const modeNote = apiKey ? '(live receipt, signed)' : '(demo receipt — add api_key for live receipts)';
  info(`${mic} → ${status} ${modeNote}`);
  if (receiptId) info(`Receipt ID: ${receiptId}`);
  if (expiresAt) info(`Expires: ${expiresAt}`);

  await writeSummary(mic, status, receipt);

  // Fail-closed logic
  if (status === 'HALTED') {
    setFailed(
      `Market ${mic} is HALTED (circuit breaker active). ` +
      `Halting workflow. Check https://headlessoracle.com/status for details.`
    );
    return;
  }

  if (status === 'UNKNOWN') {
    setFailed(
      `Market ${mic} state is UNKNOWN (oracle could not determine status). ` +
      `Treating as CLOSED per fail-closed policy. ` +
      `See SMA Protocol RFC-001: https://headlessoracle.com/docs/sma-protocol/rfc-001`
    );
    return;
  }

  if (status === 'CLOSED' && !allowClosed) {
    setFailed(
      `Market ${mic} is CLOSED and allow_closed=false. ` +
      `Next session: check https://api.headlessoracle.com/v5/schedule?mic=${mic}`
    );
    return;
  }

  if (status === 'OPEN') {
    info(`✅ ${mic} is OPEN — safe to proceed.`);
  } else {
    // CLOSED with allowClosed=true
    warning(
      `${mic} is CLOSED. Workflow continues because allow_closed=true. ` +
      `Set allow_closed=false to fail on CLOSED.`
    );
  }
}

run().catch((err) => {
  setFailed(`Unexpected error: ${err.message}`);
});
