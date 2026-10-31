import { HarnessAgent } from '@ai-sdk/harness/agent';
import type { HarnessV1 } from '@ai-sdk/harness';
import { createCodex } from '@ai-sdk/harness-codex';
import { createClaudeCode } from '@ai-sdk/harness-claude-code';
import { createVercelNetworkSandboxSession } from '@ai-sdk/sandbox-vercel';
import { stepCountIs } from 'ai';
import { modelId, requiredEnvironment, type HarnessProfile } from './config.ts';

export function createConfiguredHarness(profile: HarnessProfile, environment: NodeJS.ProcessEnv): HarnessV1 {
  const auth = Object.fromEntries(Object.entries(profile.authEnv)
    .map(([target, source]) => [target, requiredEnvironment(environment, source)]));
  const harness = profile.harness === 'codex'
    ? createCodex({ auth, reasoningEffort: profile.reasoningEffort, webSearch: profile.webSearch })
    : createClaudeCode({ auth, maxTurns: profile.maxSteps });
  for (const name of profile.activeTools) {
    if (!(name in harness.builtinTools)) throw new Error(`Unknown builtin tool for ${profile.harness}: ${name}`);
  }
  return harness;
}

export async function generateHarness(profile: HarnessProfile, environment: NodeJS.ProcessEnv,
  prompt: string, signal: AbortSignal) {
  const agent = new HarnessAgent({
    harness: createConfiguredHarness(profile, environment), model: modelId(profile, environment),
    permissionMode: profile.permissionMode, activeTools: profile.activeTools,
    stopWhen: stepCountIs(profile.maxSteps),
  });
  const sandbox = await createVercelNetworkSandboxSession({
    runtime: profile.sandbox.runtime, ports: profile.sandbox.ports,
    template: await agent.getSandboxTemplate(), abortSignal: signal,
  });
  try {
    signal.throwIfAborted();
    const session = await agent.createSession({ sandboxSession: sandbox, abortSignal: signal });
    try { return await agent.generate({ session, prompt, abortSignal: signal }); }
    finally { await session.destroy(); }
  } finally { await sandbox.destroy(); }
}
