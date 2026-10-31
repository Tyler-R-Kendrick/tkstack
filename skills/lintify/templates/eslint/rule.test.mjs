import { RuleTester } from 'eslint';
import rule from './require-audit-reason.mjs';

new RuleTester().run('require-audit-reason', rule, {
  valid: [
    'auditEvent({reason: "approved change"})',
    'auditEvent({"reason": "scheduled cleanup", actor: 7})',
    'otherCall({})',
    'logger.auditEvent({})',
    'const example = "auditEvent({})"',
  ],
  invalid: [
    'auditEvent()',
    'auditEvent({})',
    'auditEvent({reason: " "})',
    'auditEvent({reason: 1})',
    'auditEvent({reason: "first", reason: "second"})',
    'auditEvent({reason: "first", ...context})',
    'auditEvent({reason: "first", [key]: value})',
    'auditEvent({reason: "first"}, options)',
    'auditEvent({get reason() { return "reason" }})',
  ].map(code => ({ code, errors: [{ messageId: 'reason', type: 'CallExpression' }] })),
});
