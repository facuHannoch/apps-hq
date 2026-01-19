Instructions for AI Agents
Read `PROCESS.md` for a better understanding about the common processes and systems.

---

RULES TO FOLLOW

- Always work on a different than main AND in a workspace different than main (worktree or separate clone). Never edit files in the main workspace and never edit the main branch.
Before starting: read DESIGN.md (and TASKS.md if present) and follow them strictly.

- Branch naming: <prefix>/<agent_letter>/<task/topic>. For example: ai/a/seo-info or ai/a/seoandcompliance pages (both are valid).
- You have a file associated within the `agents/` directory on which you should outline your plan. This plan has to be approved before working on it. The file will have a naming convention similar to the branch or worktree: `agents/aiagent-a-seoandcompliancepages.md`. This file has two big sections: ## Plan and ## LOG. On Log, you should put what you did, but very briefly. It is a section where you will write important considerations or decisions that you taken.

- “use deploy key stored in ~/.ssh/ and loaded via ssh-agent on boot”.


Agents registered:
<agent_name>: <specialization (if given)>
