# Issue tracker: GitHub

This repository tracks issues and specs in
`Tyler-R-Kendrick/tkstack` on GitHub. Use that explicit repository when a command
could otherwise select an upstream skills repository.

- Read: `gh issue view <number> --repo Tyler-R-Kendrick/tkstack`.
- List: `gh issue list --repo Tyler-R-Kendrick/tkstack`.
- Publish a spec or ticket: create a GitHub issue in this repository, using a
  body file to preserve multiline content.
- Comment, label, close, or create issues when the user's task authorizes that
  operation. A request to install skills alone does not create tickets.
- Represent blockers with GitHub's native issue dependencies where available;
  otherwise use a `Blocked by: #<number>` line in the ticket body.

**PRs as a request surface: no.** PRs are changes for review; issue triage does
not treat external PRs as feature requests by default.
