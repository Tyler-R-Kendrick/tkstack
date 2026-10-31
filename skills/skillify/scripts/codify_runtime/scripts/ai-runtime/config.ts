import { z } from 'zod';

const envName = z.string().regex(/^[A-Za-z_][A-Za-z0-9_]*$/);
const options = z.record(z.string(), z.record(z.string(), z.json())).default({});
const provider = z.object({
  kind: z.enum(['openai', 'gateway', 'typesafe']),
  apiKeyEnv: envName,
  baseURL: z.url().optional(),
}).strict();
const common = {
  model: z.string().min(1).optional(),
  modelEnv: envName.optional(),
  timeoutMs: z.int().min(1).max(300_000).default(30_000),
};
const profile = z.discriminatedUnion('kind', [
  z.object({ ...common, kind: z.literal('language'), provider: z.string().min(1),
    api: z.enum(['chat', 'responses', 'gateway']),
    maxOutputTokens: z.int().min(1).max(32_768).default(1024),
    maxRetries: z.int().min(0).max(2).default(0), providerOptions: options }).strict(),
  z.object({ ...common, kind: z.literal('decision'), provider: z.string().min(1),
    maxRetries: z.int().min(0).max(2).default(0), providerOptions: options }).strict(),
  z.object({ ...common, kind: z.literal('harness'), harness: z.enum(['codex', 'claude-code']),
    authEnv: z.record(envName, envName).refine(value => Object.keys(value).length > 0),
    permissionMode: z.enum(['allow-reads', 'allow-edits', 'allow-all']),
    activeTools: z.array(z.string()).max(32),
    maxSteps: z.int().min(1).max(32).default(1),
    reasoningEffort: z.enum(['low', 'medium', 'high', 'xhigh', 'max']).optional(),
    webSearch: z.boolean().default(false),
    sandbox: z.object({ provider: z.literal('vercel'), runtime: z.literal('node24'),
      ports: z.array(z.int().min(1024).max(65535)).min(1).max(8) }).strict(),
  }).strict(),
]);

export const configSchema = z.object({
  version: z.literal(1),
  maxConcurrency: z.int().min(1).max(16).default(4),
  maxPending: z.int().min(0).max(64).default(32),
  providers: z.record(z.string().min(1), provider),
  profiles: z.record(z.string().min(1), profile),
}).strict().superRefine((config, context) => {
  for (const [name, entry] of Object.entries(config.profiles)) {
    const error = (message: string) => context.addIssue({ code: 'custom', path: ['profiles', name], message });
    if ((entry.model === undefined) === (entry.modelEnv === undefined)) error('Supply exactly one of model or modelEnv');
    if (entry.kind === 'harness') {
      const allowed = entry.harness === 'codex'
        ? ['OPENAI_API_KEY', 'CODEX_API_KEY', 'OPENAI_BASE_URL', 'OPENAI_ORGANIZATION', 'OPENAI_PROJECT']
        : ['ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN', 'ANTHROPIC_BASE_URL'];
      if (Object.keys(entry.authEnv).some(key => !allowed.includes(key))) error('Unsupported explicit harness authentication variable');
      if (entry.harness === 'codex' && entry.permissionMode !== 'allow-all') error('Pinned Codex adapter requires an explicit allow-all permission mode');
      if (entry.harness === 'claude-code' && entry.reasoningEffort !== undefined) error('reasoningEffort here is a Codex setting');
      continue;
    }
    const selected = config.providers[entry.provider];
    if (!selected) { error('Unknown provider'); continue; }
    if (entry.kind === 'language' &&
        !((selected.kind === 'openai' && entry.api !== 'gateway') ||
          (selected.kind === 'gateway' && entry.api === 'gateway'))) error('Provider does not implement this language API');
  }
});

export type RuntimeConfig = z.infer<typeof configSchema>;
export type HarnessProfile = Extract<RuntimeConfig['profiles'][string], {kind: 'harness'}>;

export function requiredEnvironment(environment: NodeJS.ProcessEnv, name: string): string {
  const value = environment[name];
  if (!value?.trim()) throw new Error(`Missing configured environment variable: ${name}`);
  return value;
}

export function modelId(profile: RuntimeConfig['profiles'][string], environment: NodeJS.ProcessEnv): string {
  return profile.model ?? requiredEnvironment(environment, profile.modelEnv!);
}
