import rule from './require-audit-reason.mjs';

export default [{
  files: ['fixtures/**/*.js'],
  plugins: { local: { rules: { 'require-audit-reason': rule } } },
  rules: { 'local/require-audit-reason': 'error' },
}];
