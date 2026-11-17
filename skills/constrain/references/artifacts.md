# Artifact and binary size

Record the deployed unit, bytes measured, hosting limit and provenance, and
feature value for any permitted growth. A build artifact's environmental ceiling
and growth allowance are separate hard checks; a version bump or a bigger
baseline alone is not evidence of value. Compare like architectures and build
modes. A source checkout, a compressed archive, and an expanded site are
separate measurements.

`--category artifacts` checks configured literal files or expanded directories
after the build, including Git-ignored files. It fails on missing artifacts,
symlinks, special files, absolute ceiling, per-file/count or growth breaches. `all` includes configured artifacts. The Git hook intentionally
cannot check an unbuilt artifact. Tkstack currently has no Pages deployment or
binary artifact configured. Point directory checks at the actual expanded publish directory; a ZIP file
does not establish the unpacked site size.
