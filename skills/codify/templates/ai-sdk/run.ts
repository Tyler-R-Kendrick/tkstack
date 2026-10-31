import { readFile } from 'node:fs/promises';
import { parseArgs } from 'node:util';
import { createInference } from './inference.ts';
import { execute, inputSchema, outputSchema } from './workflow.ts';

try {
  const { values } = parseArgs({ options: { input: { type: 'string' }, config: { type: 'string' } } });
  if (!values.input) throw new Error('Supply --input <json-file>');
  const raw = await readFile(values.input, 'utf8');
  if (Buffer.byteLength(raw) > 1024 * 1024) throw new Error('Input exceeds 1 MiB');
  const input = inputSchema.parse(JSON.parse(raw));
  const config = JSON.parse(await readFile(values.config ?? new URL('./profiles.json', import.meta.url), 'utf8'));
  const result = outputSchema.parse(await execute(input, createInference(config)));
  process.stdout.write(JSON.stringify(result) + '\n');
} catch (error) {
  const incomplete = error instanceof Error && error.message === 'WORKFLOW_NOT_IMPLEMENTED';
  process.stderr.write(incomplete ? 'WORKFLOW_NOT_IMPLEMENTED\n' : 'Workflow failed; inspect input/configuration and native validation.\n');
  process.exitCode = incomplete ? 3 : 1;
}
