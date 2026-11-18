'use strict';
// Fixed deterministic Promptfoo assertions over judgments already made by the
// invoking agent. No provider, model, project config, or custom code is loaded.
const fs = require('node:fs');
const path = require('node:path');
const net = require('node:net');
const tls = require('node:tls');
const http = require('node:http');
const https = require('node:https');
const blocked = () => { throw new Error('Network access is disabled for offline calibration'); };
net.connect = net.createConnection = tls.connect = http.request = http.get = https.request = https.get = blocked;
globalThis.fetch = blocked;
const promptfoo = require(path.join(process.cwd(), '.tkstack/runtime/evalify/node_modules/promptfoo'));

async function main() {
  const input = JSON.parse(fs.readFileSync(0, 'utf8'));
  let matched = 0, total = 0, passed = 0, current = 0;
  const confusion = {true_positive: 0, true_negative: 0, false_positive: 0, false_negative: 0};
  for (const item of input.cases) {
    if (item.reference === null) {
      current += 1;
      passed += Number(item.judgment);
      continue;
    }
    const result = await promptfoo.assertions.runAssertion({
      assertion: {type: 'equals', value: item.reference ? 'pass' : 'fail'},
      test: {},
      providerResponse: {output: item.judgment ? 'pass' : 'fail'},
    });
    if (typeof result.pass !== 'boolean') throw new Error('Invalid assertion result');
    total += 1;
    matched += Number(result.pass);
    const key = item.judgment ? (item.reference ? 'true_positive' : 'false_positive')
      : (item.reference ? 'false_negative' : 'true_negative');
    confusion[key] += 1;
  }
  const durations = input.cases.map(item => item.elapsed_ms).filter(value => value !== null).sort((a, b) => a - b);
  const middle = Math.floor(durations.length / 2);
  const median = durations.length === 0 ? null : durations.length % 2
    ? durations[middle] : durations[middle - 1] / 2 + durations[middle] / 2;
  const timing = {observed: durations.length, missing: input.cases.length - durations.length,
    median_ms: median, max_ms: durations.length ? durations[durations.length - 1] : null};
  process.stdout.write(JSON.stringify({calibration: {matched, total, confusion}, current: {passed, total: current}, timing}));
}
main().catch(error => { process.stderr.write(String(error)); process.exitCode = 1; });
