#!/usr/bin/env python3
"""PreToolUse guard for Orchestrator output style.

Denies source edits and mutating git in the MAIN session while the Orchestrator
output style is active. Subagents and teammates are untouched — they are the
implementors. Exits 0 (no decision) in every other case, so this is inert unless
you are actually in orchestrator mode.
"""
import json
import os
import re
import shlex
import sys

WRITABLE = ("docs/specs/", "docs/reviews/", ".claude/orchestrator/")
EDIT_TOOLS = {"Edit", "Write", "NotebookEdit"}
MUTATING_GIT = re.compile(
    r"\bgit\s+(?:-C\s+\S+\s+)?(?:add|commit|checkout|switch|restore|reset|push|stash|merge|"
    r"rebase|cherry-pick|revert|rm|mv|apply|am|clean|tag|branch\s+-[dDmM])\b"
)
REDIRECT = re.compile(r"(?<![0-9<>])>>?\s*(?!/dev/null)(?!&)(\S+)")
MUTATING_CMDS = {
    "rm", "rmdir", "mv", "cp", "mkdir", "touch", "chmod", "chown",
    "ln", "install", "truncate", "tee", "patch", "dd",
}
INPLACE = re.compile(r"^(?:sed|perl|ruby|gawk)$")


def deny(reason):
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        },
        sys.stdout,
    )
    sys.exit(0)


def output_style(cwd):
    candidates = [
        os.path.join(cwd, ".claude", "settings.local.json"),
        os.path.join(cwd, ".claude", "settings.json"),
        os.path.expanduser("~/.claude/settings.json"),
    ]
    for path in candidates:
        try:
            with open(path) as fh:
                style = json.load(fh).get("outputStyle")
        except (OSError, ValueError):
            continue
        if style:
            return style
    return None


def writable(path, cwd):
    if not path:
        return False
    rel = os.path.relpath(os.path.abspath(os.path.join(cwd, path)), cwd)
    # trailing slash so "docs/specs" matches the "docs/specs/" prefix exactly
    probe = rel if rel.endswith("/") else rel + "/"
    return any(probe.startswith(prefix) for prefix in WRITABLE)


def main():
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return

    # Subagents and teammates do the implementing. Only guard the main session.
    if event.get("agent_id"):
        return
    cwd = event.get("cwd") or os.getcwd()
    if output_style(cwd) != "Orchestrator":
        return

    tool = event.get("tool_name", "")
    args = event.get("tool_input") or {}

    if tool in EDIT_TOOLS:
        target = args.get("file_path") or args.get("notebook_path") or ""
        if writable(target, cwd):
            return
        deny(
            f"Orchestrator mode: you do not edit source. {target or 'This file'} is outside "
            "docs/specs/ and docs/reviews/. Delegate this change to an implementor agent "
            "with a self-contained brief instead."
        )

    if tool == "Bash":
        check_bash(args.get("command", ""), cwd)


def segments(cmd):
    """Split a shell line into command-position segments, ignoring quoted text."""
    out, buf, quote = [], [], None
    i = 0
    while i < len(cmd):
        c = cmd[i]
        if quote:
            if c == quote:
                quote = None
            buf.append(c)
        elif c in "'\"":
            quote = c
            buf.append(c)
        elif c in ";|&\n":
            out.append("".join(buf))
            buf = []
            # collapse && and ||
            while i + 1 < len(cmd) and cmd[i + 1] in "|&":
                i += 1
        else:
            buf.append(c)
        i += 1
    out.append("".join(buf))
    return [s.strip() for s in out if s.strip()]


def check_bash(cmd, cwd):
    # The guard stops the lazy path, not a determined one — the output style already
    # says not to route around it. So the escape hatch is deliberately explicit and
    # visible in the transcript: the user can see exactly what was authorised.
    if "ORCHESTRATOR_COMMIT=1" in cmd:
        return

    for seg in segments(cmd):
        try:
            tokens = shlex.split(seg)
        except ValueError:
            tokens = seg.split()
        if not tokens:
            continue

        # skip leading env assignments and common wrappers
        idx = 0
        while idx < len(tokens) and ("=" in tokens[idx] and not tokens[idx].startswith("-")):
            idx += 1
        while idx < len(tokens) and tokens[idx] in ("sudo", "env", "command", "nohup", "time"):
            idx += 1
        if idx >= len(tokens):
            continue

        head = os.path.basename(tokens[idx])
        rest = tokens[idx + 1:]

        if head == "git":
            joined = " ".join(rest)
            if MUTATING_GIT.search("git " + joined):
                deny(
                    "Orchestrator mode: mutating git is the implementor's job. Read-only git "
                    "(status, diff, log, rev-list, show, worktree list) is allowed. If the "
                    "user explicitly asked you to commit, prefix the command with "
                    "ORCHESTRATOR_COMMIT=1 so the authorisation is visible."
                )
            continue

        if INPLACE.match(head) and any(
            a.startswith("-i") or a.startswith("-pi") or a == "--in-place" for a in rest
        ):
            deny("Orchestrator mode: in-place file editing via shell is still implementing.")

        if head in MUTATING_CMDS:
            targets = [a for a in rest if not a.startswith("-")]
            if not targets or not all(writable(t, cwd) for t in targets):
                deny(
                    f"Orchestrator mode: `{head}` mutates the tree. Only docs/specs/ and "
                    "docs/reviews/ are yours to write. Delegate the change instead."
                )

    for target in REDIRECT.findall(cmd):
        if not writable(target, cwd):
            deny(
                "Orchestrator mode: shell redirection may only write under docs/specs/ or "
                "docs/reviews/."
            )


if __name__ == "__main__":
    main()
