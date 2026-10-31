export default {
  meta: {
    type: 'problem',
    docs: { description: 'Require an explicit literal reason in direct auditEvent calls.' },
    schema: [],
    messages: { reason: 'Use one object argument with a static nonblank string reason and no spreads or computed keys.' },
  },
  create(context) {
    return {
      CallExpression(node) {
        if (node.callee.type !== 'Identifier' || node.callee.name !== 'auditEvent') return;
        const argument = node.arguments[0];
        const object = node.arguments.length === 1 && argument?.type === 'ObjectExpression';
        const properties = object ? argument.properties : [];
        const staticKeys = properties.every(property => property.type === 'Property' && !property.computed);
        const reasons = properties.filter(property => property.type === 'Property' &&
          !property.computed && (property.key.name === 'reason' || property.key.value === 'reason'));
        const value = reasons.length === 1 ? reasons[0].value : undefined;
        if (!(object && staticKeys && reasons[0]?.kind === 'init' && value?.type === 'Literal' &&
              typeof value.value === 'string' && value.value.trim().length > 0)) {
          context.report({ node, messageId: 'reason' });
        }
      },
    };
  },
};
