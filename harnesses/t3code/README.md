# t3code

t3code does not have its own skills directory. It is an orchestrator: it runs
Claude, Codex, Cursor, Copilot, or Grok and reads the skills that host already
loaded.

`harnesses/skills.json` `delegates.t3code` names those hosts. The installer
does not create a t3code skills path. Repo-quality counts t3code as covered
when every named host is itself a harness the installer links.
