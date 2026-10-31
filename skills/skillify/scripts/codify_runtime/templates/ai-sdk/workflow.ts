import { z } from 'zod';
import type { createInference } from './inference.ts';

export const inputSchema = z.object({}).strict();
export const outputSchema = z.object({}).strict();
export type Inference = ReturnType<typeof createInference>;

export async function execute(input: z.infer<typeof inputSchema>, inference: Inference) {
  // TODO(SKILLIFY): Define actual schemas and port the procedure; call inference only for residual decisions/generation.
  void input; void inference;
  throw new Error('WORKFLOW_NOT_IMPLEMENTED');
}
