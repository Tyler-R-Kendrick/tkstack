# Grok Build source findings

This skill is an independent implementation of correction capture and procedural
improvement. It is not an extracted copy of Grok Build's `/learn` prompt.

## What the public repository contains

The inspected revision of `xai-org/grok-build` is
`2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8`. Its complete, non-truncated Git
tree contains 5,102 entries and no path containing `learn` or named `SKILL.md`.
Code search finds the `origin: learn` provenance mechanism, not a learn prompt.
This finding applies to that checked public snapshot, not every historical or
private xAI repository or every runtime bundle.

The relevant public implementation is:

- [Bundle downloads](https://github.com/xai-org/grok-build/blob/2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8/crates/codegen/xai-grok-shell/src/remote/client.rs#L74):
  the client tries `<cli-chat-proxy-base>/bundle/archive`, with legacy
  `<base>/subagents/bundle` fallback. The documented legacy route is
  `/v1/subagents/bundle`; requests use the normal session/deployment-key auth.
- [Authenticated sync](https://github.com/xai-org/grok-build/blob/2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8/crates/codegen/xai-grok-shell/src/extensions/bundle.rs#L15):
  sync requires a usable authentication source and writes the bundle cache.
- [Cache layout](https://github.com/xai-org/grok-build/blob/2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8/crates/codegen/xai-grok-bundle/src/lib.rs#L490):
  the cache root is `<grok home>/bundled`; a skill named `learn` maps to
  `skills/learn/SKILL.md`. The manifest records managed-file checksums and the
  writer preserves user-modified files.
- [Discovery](https://github.com/xai-org/grok-build/blob/2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8/crates/codegen/xai-grok-agent/src/prompt/skills.rs#L40):
  server and bundled skill roots are injected alongside local/user skills.
  Local and user names can shadow a bundled skill.
- [Generated-skill provenance](https://github.com/xai-org/grok-build/blob/2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8/crates/codegen/xai-grok-tools/src/implementations/skills/types.rs#L60):
  Grok recognizes a provider-specific `origin` frontmatter slug such as `learn`.

The separate Grok chat-product skill catalog can advertise server-expanded
skills without local bodies; see
[skills_client.rs](https://github.com/xai-org/grok-build/blob/2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8/crates/codegen/xai-grok-shell/src/remote/skills_client.rs#L11).
That is a different path from Build's on-disk bundle. The public loader alone
does not establish which payload currently supplies the user's `/learn`.

## Find the actual body on a Grok host

After normal authenticated Grok startup has populated its cache, inspect:

```sh
grok inspect --json
python3 <learn-directory>/scripts/learn.py locate-grok
python3 <learn-directory>/scripts/learn.py locate-grok --grok-home /path/to/grok-home
```

The expected bundled path is `~/.grok/bundled/skills/learn/SKILL.md` unless the
Grok home was relocated. A user override can be under `~/.grok/skills/learn/`,
or a legacy command under `~/.grok/commands/learn.md`.

The locator reports paths, hashes, and bundle-manifest matches without printing
the body, reading auth files, contacting xAI, or executing the skill. It skips
file links resolving outside the selected Grok home. A checksum mismatch means
the file differs from the managed bundle; it is not proof of authenticity.

This repository already supplies a custom `learn`, so Grok's normal discovery
may select it ahead of the platform copy. Read the `source` path from inspect
or inspect the bundled path directly rather than assuming every `/learn` is
xAI's. No Grok executable or populated cache was available in this environment.

## What is incorporated here

The portable implementation adds explicit report-only review, bounded skill
improvement from real task evidence, and stale/conflicting-instruction and
integration audits to the existing correction-to-rule loop. Experiences remain
separate from user corrections and active steering. Templates preserve the
baseline, provenance, proposed diff, validation, and disposition.

[xAI's current skills documentation](https://docs.x.ai/build/features/skills-plugins-marketplaces)
verifies the package/discovery format; its
[product page](https://x.ai/build) describes capturing a session as `/skillify`.
A [third-party September report](https://aicoder.com/news/news-20260920-grok-build-learn)
describes `/learn` mining chats, proposing skills, and auditing stale rules and
rarely observed integrations. That report is behavior context, not first-party
source or proof of a current implementation. No exact prompt, algorithm parity,
or runtime payload was recovered or claimed.
