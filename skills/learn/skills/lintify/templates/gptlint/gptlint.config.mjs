export default [{
  files: ['fixtures/**/*.js'],
  ruleFiles: ['.gptlint/comment-implementation-agreement.md'],
  rules: { 'comment-implementation-agreement': 'warn' },
  linterOptions: { concurrency: 2 },
}];
