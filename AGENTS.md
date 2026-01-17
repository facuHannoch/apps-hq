Instructions for AI Agents
Read `PROCESS.md` for a better understanding about the common processes and systems.

---

RULES TO FOLLOW

- Always work on a separate branch AND in a separate workspace (worktree or separate clone). Never edit files in the main workspace.
Before starting: read DESIGN.md (and TASKS.md if present) and follow them strictly.

- All work you do must be in a separate branch. To identify it easily, always create each branch with a prefix, like, like ai_worker_a-feature1, being "ai_worker_a" the prefix. Preferably use a name or identifier that you were given, but otherwise give yourself a name
- Branch naming: ai/<agent>/<task> (example: ai/a/seo-info).

- “use deploy key stored in ~/.ssh/ and loaded via ssh-agent on boot”


Agents registered:
<agent_name>: <specialization (if given)>
