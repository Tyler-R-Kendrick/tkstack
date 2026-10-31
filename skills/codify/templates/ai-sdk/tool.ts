import { tool } from 'ai';
import { execute, inputSchema, outputSchema, type Inference } from './workflow.ts';

export function createWorkflowTool(inference: Inference) {
  return tool({
    description: @DESCRIPTION_JSON@,
    inputSchema, outputSchema,
    execute: async input => outputSchema.parse(await execute(inputSchema.parse(input), inference)),
  });
}
