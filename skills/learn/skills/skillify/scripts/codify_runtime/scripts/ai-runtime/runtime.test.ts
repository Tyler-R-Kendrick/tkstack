import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createInference } from './inference.ts';
import { configSchema } from './config.ts';
import { createConfiguredHarness } from './harness.ts';
import { createLimiter } from './limits.ts';

const environment = { LOCAL_TEST_KEY: 'fixture-only', LOCAL_MODEL: 'fixture-model' };
const base = {
  version: 1,
  providers: { direct: { kind: 'openai', apiKeyEnv: 'LOCAL_TEST_KEY', baseURL: 'https://fixture.invalid/v1' } },
  profiles: {
    chat: { kind: 'language', provider: 'direct', api: 'chat', modelEnv: 'LOCAL_MODEL' },
    responses: { kind: 'language', provider: 'direct', api: 'responses', model: 'fixture-model' },
    decision: { kind: 'decision', provider: 'direct', model: 'fixture-model' },
  },
};
const json = (body: unknown) => new Response(JSON.stringify(body), { headers: { 'content-type': 'application/json' } });

test('native AI SDK uses distinct chat, Responses, and Decisions HTTP contracts', async () => {
  const calls: {path: string; body: Record<string, unknown>}[] = [];
  const runtime = createInference(base, { environment, fetch: async (input, init) => {
    const request = new Request(input, init);
    const path = new URL(request.url).pathname;
    assert.equal(request.headers.get('authorization'), 'Bearer fixture-only');
    calls.push({ path, body: await request.json() as Record<string, unknown> });
    if (path.endsWith('/decisions')) return json({ model: 'fixture-model', answers: [
      { type: 'predicate', name: 'ready', probability: 0.75 },
    ] });
    if (path.endsWith('/responses')) return json({ id: 'resp-fixture', created_at: 1,
      model: 'fixture-model', status: 'completed', output: [{ type: 'message', id: 'msg-fixture',
        role: 'assistant', status: 'completed', content: [{ type: 'output_text', text: 'response-result', annotations: [] }] }],
      usage: { input_tokens: 1, output_tokens: 1, total_tokens: 2 } });
    return json({ id: 'chat-fixture', created: 1, model: 'fixture-model', choices: [{ index: 0,
      message: { role: 'assistant', content: 'chat-result' }, finish_reason: 'stop' }],
      usage: { prompt_tokens: 1, completion_tokens: 1, total_tokens: 2 } });
  } });
  const messages = [{ role: 'user' as const, content: 'fixture prompt' }];
  assert.equal((await runtime.language('chat', messages)).text, 'chat-result');
  assert.equal((await runtime.language('responses', messages)).text, 'response-result');
  assert.deepEqual((await runtime.decide('decision', { observed: true }, {
    ready: { type: 'boolean', instructions: 'Is the observed state ready?' },
  })).answers.ready, { type: 'boolean', probability: 0.75 });
  assert.deepEqual(calls.map(call => call.path), ['/v1/chat/completions', '/v1/responses', '/v1/decisions']);
  assert.ok(calls.every(call => call.body.model === 'fixture-model'));
  assert.ok('messages' in calls[0].body);
  assert.ok('input' in calls[1].body);
  assert.ok('questions' in calls[2].body);
});

test('unknown profiles, missing credentials, and capability mismatches never fall back', async () => {
  let calls = 0;
  const runtime = createInference(base, { environment: {}, fetch: async () => { calls++; throw Error('unexpected request'); } });
  await assert.rejects(runtime.language('unknown', []), /Unknown inference profile/);
  await assert.rejects(runtime.language('decision', []), /not a language/);
  await assert.rejects(runtime.language('chat', []), /Missing configured environment/);
  assert.equal(calls, 0);
  assert.throws(() => createInference({ ...base, profiles: {
    bad: { kind: 'language', provider: 'direct', model: 'fixture', api: 'gateway' },
  } }), /Provider does not implement/);
  assert.throws(() => createInference({ ...base, profiles: {
    bad: { kind: 'decision', provider: 'missing', model: 'fixture' },
  } }), /Unknown provider/);
  assert.throws(() => createInference({ ...base, profiles: {
    bad: { ...base.profiles.chat, model: 'ambiguous' },
  } }), /exactly one/);
});

test('empty profiles work offline and do not reconfigure the process provider', () => {
  const before = globalThis.AI_SDK_DEFAULT_PROVIDER;
  createInference({ version: 1, providers: {}, profiles: {} }, { environment: {},
    fetch: async () => { throw Error('A deterministic step must not call a model'); } });
  assert.equal(globalThis.AI_SDK_DEFAULT_PROVIDER, before);
});

test('native decision response validation rejects an invalid probability', async () => {
  const runtime = createInference(base, { environment, fetch: async () => json({
    model: 'fixture-model', answers: [{ type: 'predicate', name: 'ready', probability: 1.5 }],
  }) });
  await assert.rejects(runtime.decide('decision', 'state', {
    ready: { type: 'boolean', instructions: 'Is it ready?' },
  }));
});

test('caller cancellation reaches native fetch and is not retried', async () => {
  const controller = new AbortController();
  let calls = 0;
  const runtime = createInference(base, { environment, fetch: async (_input, init) => {
    calls++;
    return new Promise((_resolve, reject) => {
      init!.signal!.addEventListener('abort', () => reject(init!.signal!.reason), { once: true });
      controller.abort(new Error('stop fixture'));
    });
  } });
  await assert.rejects(runtime.language('chat', [{ role: 'user', content: 'fixture' }], controller.signal));
  assert.equal(calls, 1);
});

test('shared limiter bounds active and queued work, cancels queued work, and releases failures', async () => {
  const limited = createLimiter(1, 1);
  const controller = new AbortController();
  let release!: () => void;
  let markStarted!: () => void;
  const started = new Promise<void>(resolve => { markStarted = resolve; });
  const first = limited(async () => { markStarted(); await new Promise<void>(resolve => { release = resolve; }); return 1; }, new AbortController().signal);
  await started;
  let queuedRan = false;
  const queued = limited(async () => { queuedRan = true; return 2; }, controller.signal);
  const cancelled = assert.rejects(queued, /cancel fixture/);
  await assert.rejects(limited(async () => 3, new AbortController().signal), /capacity exceeded/);
  controller.abort(new Error('cancel fixture'));
  await cancelled;
  release();
  assert.equal(await first, 1);
  assert.equal(queuedRan, false);
  await assert.rejects(limited(async () => { throw Error('fixture failure'); }, new AbortController().signal), /fixture failure/);
  assert.equal(await limited(async () => 4, new AbortController().signal), 4);
});

test('Codex and Claude profiles instantiate the official harness adapters without starting sessions', () => {
  for (const harness of ['codex', 'claude-code'] as const) {
    const key = harness === 'codex' ? 'CODEX_API_KEY' : 'ANTHROPIC_API_KEY';
    const config = configSchema.parse({ version: 1, providers: {}, profiles: { selected: {
      kind: 'harness', harness, modelEnv: 'LOCAL_MODEL', authEnv: { [key]: 'LOCAL_TEST_KEY' },
      activeTools: [], permissionMode: harness === 'codex' ? 'allow-all' : 'allow-reads',
      sandbox: { provider: 'vercel', runtime: 'node24', ports: [4000] },
    } } });
    const profile = config.profiles.selected;
    assert.equal(profile.kind, 'harness');
    if (profile.kind !== 'harness') throw Error('Wrong profile');
    const native = createConfiguredHarness(profile, environment);
    assert.equal(native.specificationVersion, 'harness-v1');
    assert.ok(native.builtinTools);
    assert.throws(() => createConfiguredHarness({ ...profile, activeTools: ['does-not-exist'] }, environment), /Unknown builtin tool/);
    assert.throws(() => createConfiguredHarness(profile, {}), /Missing configured environment/);
  }
});
