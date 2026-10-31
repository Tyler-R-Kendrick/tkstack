import { createOpenAI } from '@ai-sdk/openai';
import { createGateway } from '@ai-sdk/gateway';
import { createTypeSafeAi } from '@ai-sdk/typesafe-ai';
import { generateText, experimental_decide, type ModelMessage,
  type Experimental_DecisionState, type Experimental_DecisionQuestion } from 'ai';
import { configSchema, modelId, requiredEnvironment } from './config.ts';
import { createLimiter } from './limits.ts';
import { generateHarness } from './harness.ts';

export function createInference(configuration: unknown, services: {
  environment?: NodeJS.ProcessEnv; fetch?: typeof fetch;
} = {}) {
  const config = configSchema.parse(configuration);
  const environment = { ...(services.environment ?? process.env) };
  const limited = createLimiter(config.maxConcurrency, config.maxPending);
  function profile(name: string) {
    const entry = config.profiles[name];
    if (!entry) throw new Error(`Unknown inference profile: ${name}`);
    return entry;
  }
  function provider(name: string) {
    const entry = config.providers[name];
    if (!entry) throw new Error(`Unknown provider: ${name}`);
    const settings = { apiKey: requiredEnvironment(environment, entry.apiKeyEnv),
      baseURL: entry.baseURL, fetch: services.fetch };
    if (entry.kind === 'openai') return createOpenAI(settings);
    if (entry.kind === 'gateway') return createGateway(settings);
    return createTypeSafeAi(settings);
  }
  function signal(timeoutMs: number, parent?: AbortSignal) {
    const deadline = AbortSignal.timeout(timeoutMs);
    return parent ? AbortSignal.any([parent, deadline]) : deadline;
  }
  return {
    async language(name: string, messages: ModelMessage[], parent?: AbortSignal) {
      const entry = profile(name);
      if (entry.kind !== 'language') throw new Error('Profile is not a language model');
      const abortSignal = signal(entry.timeoutMs, parent);
      return limited(async () => {
        const selected = provider(entry.provider);
        const id = modelId(entry, environment);
        const model = entry.api === 'gateway' ? createGatewayModel(selected, id)
          : entry.api === 'chat' ? createChatModel(selected, id) : createResponsesModel(selected, id);
        return generateText({ model, messages, abortSignal, maxRetries: entry.maxRetries,
          maxOutputTokens: entry.maxOutputTokens, providerOptions: entry.providerOptions });
      }, abortSignal);
    },
    async decide<Q extends Record<string, Experimental_DecisionQuestion>>(name: string,
      state: Experimental_DecisionState, questions: Q, parent?: AbortSignal) {
      const entry = profile(name);
      if (entry.kind !== 'decision') throw new Error('Profile is not a decision model');
      const abortSignal = signal(entry.timeoutMs, parent);
      return limited(() => experimental_decide({ model: provider(entry.provider).decisionModel(modelId(entry, environment)),
        state, questions, abortSignal, maxRetries: entry.maxRetries, providerOptions: entry.providerOptions }), abortSignal);
    },
    async harness(name: string, prompt: string, parent?: AbortSignal) {
      const entry = profile(name);
      if (entry.kind !== 'harness') throw new Error('Profile is not a harness');
      const abortSignal = signal(entry.timeoutMs, parent);
      return limited(() => generateHarness(entry, environment, prompt, abortSignal), abortSignal);
    },
  };
}

// Narrow capabilities explicitly; never change transports or providers as a fallback.
function createChatModel(provider: ReturnType<typeof createOpenAI> | ReturnType<typeof createGateway> | ReturnType<typeof createTypeSafeAi>, id: string) {
  if (!('chat' in provider)) throw new Error('Provider has no Chat Completions API');
  return provider.chat(id);
}
function createResponsesModel(provider: ReturnType<typeof createOpenAI> | ReturnType<typeof createGateway> | ReturnType<typeof createTypeSafeAi>, id: string) {
  if (!('responses' in provider)) throw new Error('Provider has no Responses API');
  return provider.responses(id);
}
function createGatewayModel(provider: ReturnType<typeof createOpenAI> | ReturnType<typeof createGateway> | ReturnType<typeof createTypeSafeAi>, id: string) {
  if (!('languageModel' in provider)) throw new Error('Provider has no language model');
  return provider.languageModel(id);
}
