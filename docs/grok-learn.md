# Finding and incorporating Grok Build's learn behavior

Investigated 2026-10-29 (America/Chicago), against public commit
`2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8` of `xai-org/grok-build`.

The linked `crates/codegen` directory contains the harness and skill-loading
infrastructure. In the complete public tree at this revision there is no path
containing `learn`, no `SKILL.md`, and no dedicated `/learn` handler. Code search
does expose the generated-skill `origin: learn` marker. This does not prove
where every version of the product's `/learn` lives.

The useful source trail is:

| Responsibility | Public implementation |
| --- | --- |
| Download authenticated platform bundles | [shell remote client](https://github.com/xai-org/grok-build/blob/2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8/crates/codegen/xai-grok-shell/src/remote/client.rs#L74) |
| Synchronize the bundle after authentication | [bundle extension](https://github.com/xai-org/grok-build/blob/2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8/crates/codegen/xai-grok-shell/src/extensions/bundle.rs#L15) |
| Materialize `skills/<name>/SKILL.md` under the Grok bundled cache | [bundle cache](https://github.com/xai-org/grok-build/blob/2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8/crates/codegen/xai-grok-bundle/src/lib.rs#L490) |
| Add injected server/bundled roots to discovery | [agent skills](https://github.com/xai-org/grok-build/blob/2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8/crates/codegen/xai-grok-agent/src/prompt/skills.rs#L40) |
| Retain skill-authoring provenance such as `learn` | [skill types](https://github.com/xai-org/grok-build/blob/2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8/crates/codegen/xai-grok-tools/src/implementations/skills/types.rs#L60) |

The client first tries `<configured proxy base>/bundle/archive`, then falls
back to `<base>/subagents/bundle`. Bundle sync uses normal session or deployment
authentication. The repository publishes that transport and cache code; the
checked tree does not publish a corresponding learn prompt.

On an authenticated Grok installation, the expected bundled path is:

```text
~/.grok/bundled/skills/learn/SKILL.md
```

Find the actual discovered source or inspect the local cache without exposing
the skill body or credentials:

```sh
grok inspect --json
python3 skills/learn/scripts/learn.py locate-grok
python3 skills/learn/scripts/learn.py locate-grok --grok-home /path/to/grok-home
```

The locator reports existing bundled/user/legacy paths, SHA-256, and cached
manifest matches. It makes no network call, changes no files, and does not scan
private transcripts. No Grok binary or populated cache was available here, so
the exact runtime `/learn` prompt was not recovered or installed. A selected
cache source must be inspected before claiming a faithful reproduction.

This repository's own `learn` can shadow the bundled name: Grok also discovers
`.agents`/Claude/Cursor skills and prefers higher-priority local/user entries.
Use the reported source path, rather than assuming a `/learn` invocation is the
platform copy. The separate Grok chat-product catalog can also expand bundled
skills server-side, as explained in the
[package's detailed source findings](../skills/learn/references/grok-build.md).

## Incorporated behavior

The custom root package is upgraded to learn 0.2.0 with:

- `/learn report` and `/learn audit` for a read-only review with an explicit
  observation window, proposed actions, and uncertain findings.
- `/learn improve <skill>` for deriving a bounded reusable procedure, updating
  or creating an owned skill, retaining a baseline/diff, and validating before
  applying within the established request.
- Typed task/tool experiences that remain distinct from user corrections,
  never enter active steering automatically, and cannot authorize a rule.
- A proposal template covering provenance, ownership, transfer/boundary cases,
  actual checks, disposition, and rollback.
- Instruction and integration audits that distinguish an observed defect from
  a hypothesis or an invocation simply not observed in the available window.

This is an independent portable implementation. The public runtime establishes
discovery and provenance; first-party docs describe session-to-skill capture
as `/skillify`, while third-party reporting describes `/learn`'s broader audit
behavior. Neither supplies a recovered learn prompt here. No hidden algorithm,
exact prompt parity, or measured model improvement is claimed.

The installed symlinks still point to `skills/learn`, and the root marketplace
catalog records its new version. The SkillOpt integration remains the selected
gate for automated revisions. Tests exercise the actual new helper behavior;
historical model-decision results remain bound to their original skill hashes.
