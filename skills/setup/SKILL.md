---
name: setup
description: Check that the orchestrator plugin is fully wired — plugins, harnesses, tools, bus, output style — and walk through fixing whatever is missing. Run after installing, or when delegation or the message bus is not behaving.
disable-model-invocation: true
allowed-tools: Read, Bash(orchestrator-doctor*), Bash(~/.claude/bin/orchestrator-doctor*), Bash(~/.claude/bin/orchestrator-harnesses*), Bash(claude mcp*), Bash(ls ~/.claude/bin*)
---

# Setup

Run the doctor first, always:

```bash
~/.claude/bin/orchestrator-doctor
```

If that path does not exist, the SessionStart hook has not run yet — use
`"${CLAUDE_PLUGIN_ROOT}/scripts/orchestrator-doctor"` and tell the user to restart the session
so the symlinks get created.

## Reading the output

Three states, and they mean different things:

- **OK** — nothing to do.
- **`--` (warn)** — optional. The plugin works without it, at reduced capability. Never present
  these as errors; say what capability is missing if it stays unconfigured.
- **FAIL** — required. The plugin will not work correctly until fixed.

Every non-OK check prints the exact fix command. Use those verbatim rather than improvising.

## Presenting it

Report status grouped as: **required failures first**, then optional gaps, then a one-line
summary. Do not re-print the whole table — the user just saw it. Lead with what to do.

For anything the user must run themselves — `/plugin`, `/config`, interactive auth — hand them
the exact command and say it needs to be typed, since you cannot run slash commands. Suggest
prefixing shell commands with `!` so the output lands in the conversation.

You may run the non-interactive fixes yourself after saying which and why:

- `~/.claude/bin/orchestrator-harnesses` to create the registry
- `claude mcp add agent-bus --transport http http://127.0.0.1:8477/mcp`

Do not install anything with `npm`, `brew`, or `/plugin` without asking first.

## What each gap actually costs

Say the consequence, not just the name:

| Gap | Consequence |
| --- | --- |
| Orchestrator output style not selected | the no-implement rule is not enforced — the guard hook is inert |
| tools not on `~/.claude/bin` | role files and reference docs point at paths that do not exist |
| bus not running | roles cannot message each other; history still readable via `agent-board` |
| bus not registered as MCP | Claude agents must use REST instead of `chat_*` tools |
| a harness unavailable | you cannot get a second opinion from that model family |
| codex/grok/pi plugin missing | no background job control or review commands for that harness |
| duplicate-hooks conflict | **that plugin's hooks never run**, though its skills and agents still load |

## After a clean run

Point at what to do next rather than stopping at "ready":

```
/config -> Output style -> Orchestrator
/orchestrate <goal>
```
