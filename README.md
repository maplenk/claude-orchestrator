# orchestrator

A plan → delegate → verify workflow for Claude Code, where implementation reaches the tree only
through delegated agents and every wave is independently verified before the next one starts.

The idea it is built around: **roles and harnesses are orthogonal.** A role is the job; a
harness is the model executing it. One role definition runs on Claude, Codex, Grok or pi — there
is no per-model copy of a role.

## Install

```
/plugin marketplace add maplenk/claude-orchestrator
/plugin install orchestrator@orchestrator-marketplace
```

To hack on it, point the marketplace at a local clone instead of the GitHub repo:

```
/plugin marketplace add ~/path/to/claude-orchestrator
```

Then pick the output style: `/config` → **Output style** → `Orchestrator`.

Nothing in this plugin activates until you do. The guard hook, the workflow, and the harness
prompt are all inert under any other output style.

## What you get

| Piece | Kind | What it is |
| --- | --- | --- |
| `Orchestrator` | output style | plan, delegate, verify — never implement |
| `Developer` | output style | plan then implement yourself, no delegation |
| `/orchestrate` | skill | the wave workflow |
| `developer` | agent | scoped implementor |
| `ui-developer` | agent | front-end implementor |
| `verifier` | agent | evidence-driven check against acceptance criteria |

Plus five tools, symlinked to `~/.claude/bin/` on session start:

| Tool | Purpose |
| --- | --- |
| `run-role` | run any role on any harness |
| `orchestrator-harnesses` | probe which harnesses are reachable |
| `agent-bus` | MCP + REST message bus for cross-harness comms |
| `agent-board` | read the bus's message log without a server |
| `orchestrator-doctor` | check that everything is installed and wired |

## Why an output style and not just a skill

A skill's content enters the conversation as one message and then competes with everything
after it. Output styles modify the system prompt and get adherence reminders every turn, which
is what a session-long "you do not implement" rule actually needs.

Enforcement is a `PreToolUse` hook rather than skill frontmatter, because skill
`disallowed-tools` and skill-scoped hooks **clear on your next message** — they cannot hold a
session-long rule. The hook reads `outputStyle` from settings, no-ops unless it is
`Orchestrator`, and skips any event carrying `agent_id` so subagents can still write code.

While active it blocks `Edit`/`Write`/`NotebookEdit` outside `docs/specs/` and `docs/reviews/`,
mutating git, in-place shell edits, and redirection into source. It parses commands at command
position, so `grep -rn "rm" app/` is allowed and `git status && rm -rf app/` is not.

When you explicitly ask for a commit, prefix it with `ORCHESTRATOR_COMMIT=1` — committing is a
legitimate part of the workflow, and the prefix keeps the authorisation visible in the
transcript rather than hidden in a config flag.

## Harnesses

```bash
~/.claude/bin/orchestrator-harnesses           # probe + print
~/.claude/bin/run-role developer --harness pi -- "<brief>"
~/.claude/bin/run-role verifier --harness codex --read-only -- "<brief>"
```

`run-role` strips the frontmatter from the role file and passes the body via
`--append-system-prompt`. This works because the codex/grok adapters drive *headless Claude
Code* pointed at a local proxy, and pi accepts the same flag.

Roles resolve from your own `~/.claude/agents/` first and fall back to the plugin's, so you can
override a packaged role without editing the plugin.

Model choice belongs to the **role × harness pair**, not the harness alone. `harnesses.json`
takes a `modelByRole` map — e.g. pi runs Kimi for `ui-developer` and DeepSeek for everything
else. Resolution order is `--model` > `modelByRole[role]` > `model`.

Set `RUN_ROLE_THINKING` (default `medium`) if runs are too slow or not thorough enough.

Pass `--worktree` to run a role in its own checkout, so concurrent delegations cannot collide
over a shared index. It is opt-in by design — where an agent's work lands is your call, not a
silent default. The branch, its base SHA, and the merge and cleanup commands are printed when
it starts.

Each non-Claude harness also has a first-party plugin worth installing alongside this one, for
background job control and review commands: `openai/codex-plugin-cc`,
`xai-org/grok-build-plugin-cc`, `Agents365-ai/pi-plugin-cc`.

## Comms

`SendMessage` reaches Claude agents only — codex, grok and pi are headless CLI processes with
no mailbox, and messages to them vanish silently. So the plugin ships a bus on
`127.0.0.1:8477`: MCP for Claude, REST for everything else, one JSONL store.

```
claude mcp add agent-bus --transport http http://127.0.0.1:8477/mcp
```

Tools: `chat_register`, `chat_send`, `chat_read`, `chat_wait`, `chat_who`.

Three deliberate design choices:

- **Long-poll, not keystroke injection.** You cannot wake an idle Claude Code subagent from
  outside — it is not a terminal and only exists inside a tool call. `chat_wait` blocks
  server-side and releases when a message lands.
- **Identity is issued, not claimed.** `register` returns a token; the server maps token → name
  and stamps messages itself, so an agent cannot post as another role.
- **Fixed port, not ephemeral.** MCP servers connect at session start, so a bus on a random
  port would be REST-only. A second session finds the port bound and reuses it; traffic is
  separated by channel, which defaults to the git branch.

Loop guard refuses messages past 6 hops.

## Tests

```bash
tests/run-tests              # all suites
tests/run-tests guard        # guard | bus | role
```

51 checks, no dependencies, no network. The bus suite starts its own server on port 8479 so it
never disturbs a running one. The guard suite is the one that matters most — its allow/deny
matrix is easy to break with a well-meaning regex change.

## Developing on this plugin

Installing from a local path **copies** the repo into
`~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/`. `/reload-plugins` does not re-copy
when the version is unchanged, so edits to the repo will not take effect. Either bump `version`
in `plugin.json`, or sync the cache directly:

```bash
rsync -a --delete --exclude='.git' ./ \
  ~/.claude/plugins/cache/orchestrator-marketplace/orchestrator/0.1.0/
```

Do not declare `"hooks": "./hooks/hooks.json"` in `plugin.json` — that path is auto-loaded, and
naming it again fails the whole hooks block with "Duplicate hooks file detected".

## What this plugin does to your machine

Stated plainly, because two of these are unusual for a plugin and you should know before
installing.

**Hooks it registers**

| Hook | Fires | What it does |
| --- | --- | --- |
| `SessionStart` | once per session start | Symlinks five scripts into `~/.claude/bin/`, then starts the message bus if nothing already holds its port. |
| `PreToolUse` | every `Edit`, `Write`, `NotebookEdit`, `Bash` call | Reads the tool's arguments to decide whether to block it. Returns immediately unless the `Orchestrator` output style is active. |

The `PreToolUse` hook is deliberately broad — blocking source edits is the plugin's whole
purpose, and a narrower matcher could not enforce it. It is gated three ways: it exits
immediately unless `outputStyle` is exactly `Orchestrator`, it ignores any event carrying an
`agent_id` (subagents must be able to write), and it only ever *denies* — it cannot modify a
call. [Read it](hooks/orchestrator-guard.py); it is ~170 lines with no network access.

**It writes outside the plugin directory**

- `~/.claude/bin/` — five symlinks, and only if the name is free or already points at this
  plugin. A real file there is never replaced.
- `~/.claude/orchestrator/harnesses.json` — your harness registry.
- `.claude/orchestrator/` in the working repo — bus handshake and message log, self-gitignored.

**It runs a local server**

`agent-bus` binds `127.0.0.1:8477` and stays up for the session. It is bound to loopback only.
Set `AGENT_BUS_PORT` to move it; kill it with `agent-bus stop` or by port.

**Network**

No outbound internet calls. The plugin's own code talks only to `127.0.0.1` — its bus, and
CLIProxyAPI's model list when probing harness availability. `run-role` shells out to `claude`
or `pi`, which make their own provider calls under your existing credentials; the plugin does
not read, store, or forward those credentials.

**No telemetry.** Nothing is collected or sent anywhere.

## Configuration

| Path | What |
| --- | --- |
| `~/.claude/orchestrator/harnesses.json` | harness registry — your `default`, `model`, `modelByRole`, `askPerWave` edits survive probing |
| `.claude/orchestrator/board/<channel>.jsonl` | message log, gitignored |
| `.claude/orchestrator/bus.json` | bus handshake (url, session, channel) |
| `AGENT_BUS_PORT` | bus port, default `8477` |
| `RUN_ROLE_THINKING` | thinking level for pi runs, default `medium` |

## Prior art

The role model is a native reimplementation of the specialist system in
[AO](https://aoagents.dev) / Intent — coordinator, implementor, verifier — rebuilt on Claude
Code primitives rather than handing off to those apps. Note that AO's `@@@task` / `intent://`
spec syntax is inert here; the native equivalent is markdown task blocks plus `TaskCreate`
dependencies, which actually enforce the wave barrier.

The bus is shaped by [agentchattr](https://github.com/bcurts/agentchattr), diverging where
Claude Code's constraints differ (see Comms above).

## License

MIT
