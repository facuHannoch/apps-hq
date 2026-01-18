#!/usr/bin/env python3
import argparse
import os
import string
import subprocess
from pathlib import Path

def sh(cmd: list[str], cwd: Path | None = None) -> None:
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)

def tmux(cmd: list[str]) -> None:
    sh(["tmux", *cmd])

def get_letter(i: int) -> str:
    letters = string.ascii_lowercase
    if i >= len(letters):
        raise ValueError("Too many agents for single-letter IDs")
    return letters[i]

"""Generates worktrees (and branches) from a list of tasks/topics and creates a tmux session with a new window for each worktree, having each window two vertical panes, initializing lazygit on the left pane (right panel is to initialize cli code).
If the worktrees and/or branches already exist, it skips that steps (does not fail)
"""
def build_worktree_and_deploy_agents(args):

    base = Path(args.base).resolve()
    wt_root = Path(args.wt_root).resolve()
    repo = args.repo
    session = args.session or repo

    tasks = [t.strip() for t in args.tasks.split(",") if t.strip()]
    if not tasks:
        raise SystemExit("No tasks parsed from --tasks")

    wt_root.mkdir(parents=True, exist_ok=True)

    # 1) Create worktrees
    for i, task in enumerate(tasks):
        a = get_letter(i)
        branch = f"{args.branch_prefix}/{a}/{task}"
        wt_dir = wt_root / f"{repo}__{args.branch_prefix}-{a}-{task}"
        # Check if branch already exists
        branch_check = subprocess.run(
            ["git", "show-ref", "--verify", f"refs/heads/{branch}"],
            cwd=base / repo,
            capture_output=True
        )
        if branch_check.returncode == 0:
            print(f"Branch {branch} already exists, skipping...")
            continue

        # Check if worktree already exists
        if wt_dir.exists():
            print(f"Worktree {wt_dir} already exists, skipping...")
            continue
        
        # Worktree add
        if branch_check.returncode == 0:
            # Branch exists, attach worktree to it
            sh(["git", "worktree", "add", str(wt_dir), branch], cwd=base / repo)
        else:
            # Branch doesn't exist, create it
            sh(["git", "worktree", "add", "-b", branch, str(wt_dir), "HEAD"], cwd=base / repo)

        # Init submodules inside worktree
        sh(["git", "submodule", "update", "--init", "--recursive"], cwd=wt_dir)

        # Per-worktree git identity (repo-local config, not global)
        sh(["git", "config", "user.name", branch], cwd=wt_dir)
        sh(["git", "config", "user.email", f"{branch.replace('/', '-') }@{args.email_domain}"], cwd=wt_dir)

    # 2) Start ssh-agent if needed (optional: you may already have it)
    # NOTE: managing ssh-agent from scripts is OS/env-specific; many people prefer manual.
    # If you want, you can add checks here, but I'd keep it manual for reliability.

    # 3) Create tmux session + windows with correct cwd
    # Create session detached, rooted at wt_root
    tmux(["new-session", "-d", "-s", session, "-c", str(wt_root)])

    # First window: rename it to agent-a
    for i, task in enumerate(tasks):
        a = get_letter(i)
        wt_dir = wt_root / f"{repo}__{args.branch_prefix}-{a}-{task}"
        win_name = f"{args.branch_prefix}/{a}/{task}"

        if i == 0:
            tmux(["rename-window", "-t", f"{session}:0", win_name])
            tmux(["send-keys", "-t", f"{session}:0", f"cd {wt_dir}", "Enter"])
            tmux(["send-keys", "-t", f"{session}:0", "lazygit", "Enter"])
            tmux(["split-window", "-t", f"{session}:0", "-h", "-c", str(wt_dir)])
        else:
            tmux(["new-window", "-t", session, "-n", win_name, "-c", str(wt_dir)])
            tmux(["send-keys", "-t", f"{session}:{i}", "lazygit", "Enter"])
            tmux(["split-window", "-t", f"{session}:{i}", "-h", "-c", str(wt_dir)])

        # Right pane target is ".1" (pane index 1 after split)
        right_pane = f"{session}:{i}.1"

        if args.start_codex:
            tmux(["send-keys", "-t", right_pane, "codex", "Enter"])
            # Then send the initial instruction
            tmux(["send-keys", "-t", right_pane, args.codex_read_prompt, "Enter"])

    # Attach
    tmux(["attach-session", "-t", session])

"""
Kills the tmux session
Removes each worktree
Deletes the branches (unless --keep-branches is specified) !!! TODO: This ok??
Handles errors gracefully if resources don't exist
"""
def destroy_tmux_sessions_and_worktrees(args):
    """Clean up tmux session, worktrees, and optionally branches."""
    base = Path(args.base).resolve()
    wt_root = Path(args.wt_root).resolve()
    repo = args.repo
    session = args.session or repo

    tasks = [t.strip() for t in args.tasks.split(",") if t.strip()]
    if not tasks:
        raise SystemExit("No tasks parsed from --tasks")

    # 1) Kill tmux session if it exists
    try:
        result = subprocess.run(
            ["tmux", "has-session", "-t", session],
            capture_output=True
        )
        if result.returncode == 0:
            print(f"Killing tmux session: {session}")
            tmux(["kill-session", "-t", session])
        else:
            print(f"Tmux session {session} not found")
    except Exception as e:
        print(f"Error checking/killing tmux session: {e}")

    # 2) Remove worktrees
    for i, task in enumerate(tasks):
        a = get_letter(i)
        branch = f"{args.branch_prefix}/{a}/{task}"
        wt_dir = wt_root / f"{repo}__{args.branch_prefix}-{a}-{task}"

        if wt_dir.exists():
            print(f"Removing worktree: {wt_dir}")
            try:
                sh(["git", "worktree", "remove", str(wt_dir)], cwd=base / repo)
            except subprocess.CalledProcessError as e:
                print(f"Error removing worktree {wt_dir}: {e}")
                print(f"You may need to manually remove: {wt_dir}")
        else:
            print(f"Worktree {wt_dir} not found")

        # 3) Delete branches if not keeping them
        if not args.keep_branches:
            # Check if branch exists
            branch_check = subprocess.run(
                ["git", "show-ref", "--verify", f"refs/heads/{branch}"],
                cwd=base / repo,
                capture_output=True
            )
            if branch_check.returncode == 0:
                print(f"Deleting branch: {branch}")
                try:
                    sh(["git", "branch", "-D", branch], cwd=base / repo)
                except subprocess.CalledProcessError as e:
                    print(f"Error deleting branch {branch}: {e}")
            else:
                print(f"Branch {branch} not found")

    print("\nCleanup complete!")

if __name__ == "__main__":

    p = argparse.ArgumentParser()
    subparsers = p.add_subparsers(dest="command", required=True)

    # Deploy subcommand
    deploy_p = subparsers.add_parser('deploy', help='Deploy agent worktrees and tmux')
    deploy_p.add_argument("--repo", required=True, help="Repo name, used for worktree folder naming")
    deploy_p.add_argument("--base", default="..", help="Base directory where main repo lives (default: ..)")
    deploy_p.add_argument("--wt-root", default="../_wt", help="Worktrees root directory (default: ../_wt)")
    deploy_p.add_argument("--tasks", required=True, help='Comma-separated, e.g. "seoandcompliancepages,app,landingpages,server"')
    deploy_p.add_argument("--branch-prefix", default="aiagent", help='Branch prefix, e.g. "aiagent"')
    deploy_p.add_argument("--session", default=None, help="tmux session name (default: repo name)")
    deploy_p.add_argument("--start-codex", action="store_true", help="Auto-run codex in right pane")
    deploy_p.add_argument("--codex-read-prompt", default="Read PROCESS.md and all the pages that it references",
                   help="Initial prompt to send to codex (only if --start-codex)")
    deploy_p.add_argument("--email-domain", default="local", help="Used for per-agent email, e.g. aiagent/a/app@local")

    # Destroy subcommand
    destroy_p = subparsers.add_parser('destroy', help='Clean up worktrees and tmux')
    destroy_p.add_argument("--repo", required=True, help="Repo name, used for worktree folder naming")
    destroy_p.add_argument("--base", default="..", help="Base directory where main repo lives (default: ..)")
    destroy_p.add_argument("--wt-root", default="../_wt", help="Worktrees root directory (default: ../_wt)")
    destroy_p.add_argument("--tasks", required=True, help='Comma-separated, e.g. "seoandcompliancepages,app,landingpages,server"')
    destroy_p.add_argument("--branch-prefix", default="aiagent", help='Branch prefix, e.g. "aiagent"')
    destroy_p.add_argument("--session", default=None, help="tmux session name (default: repo name)")
    destroy_p.add_argument("--keep-branches", default=True, action="store_true", help="Keep git branches after removing worktrees")
    

    args = p.parse_args()

    if args.command == 'deploy':
        build_worktree_and_deploy_agents(args)
    elif args.command == 'destroy':
        destroy_tmux_sessions_and_worktrees(args)
