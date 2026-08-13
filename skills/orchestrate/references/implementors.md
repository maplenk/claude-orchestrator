# Roles and harnesses

These are **orthogonal axes**. A role is the job; a harness is the model executing it. One role
definition runs on any harness — do not create a per-model copy of a role.

| | |
| --- | --- |
| **Roles** | `developer`, `ui-developer`, `verifier` — defined once in `~/.claude/agents/` |
| **Harnesses** | `claude`, `codex`, `grok`, `pi` |

## Running a role on a harness

**claude** — the Agent tool, in-process:

```
Agent(subagent_type: "orchestrator:developer", isolation: "worktree", prompt: <brief>)
```

The only harness that supports worktree isolation, so it is the default for concurrent waves.

Plugin agents are namespaced, so the Agent tool needs `orchestrator:<role>`. `run-role` takes
the bare name, because it resolves role *files* rather than registered agent types.

**codex / grok / pi** — `run-role` injects the role file as the system prompt:

```bash
~/.claude/bin/run-role developer --harness pi -- "<brief>"
~/.claude/bin/run-role verifier  --harness codex --read-only -- "<brief>"
~/.claude/bin/run-role ui-developer --harness grok --model grok-4.6 -- "<brief>"
```

It strips the frontmatter from `~/.claude/agents/<role>.md` and passes the body via
`--append-system-prompt`, so `verifier` behaves like `verifier` whichever model is behind it —
verified: pi/Kimi reproduces the verifier's verdict format and its "no evidence, no
verification" rule. `--read-only` maps to each harness's strict read-only setting.

## Registry

`~/.claude/orchestrator/harnesses.json`, refreshed by:

```bash
~/.claude/bin/orchestrator-harnesses          # probe + print
~/.claude/bin/orchestrator-harnesses --json   # merged registry
~/.claude/bin/orchestrator-harnesses --no-probe
```

Probing overwrites `available` and `detail` only — your `default`, `model`, `plugin` and
`notes` edits survive, so pinning a model is a one-time edit rather than a flag every run.

An unavailable harness is never offered. Never fall back silently: "the proxy was down so I
used Claude" is exactly the substitution that invalidates a comparison later.

## Asking

Before delegating a wave, ask the user which harness — one `AskUserQuestion` with the
**available** harnesses, registry `default` first and marked `(Recommended)`, each option
carrying its `detail`. Ask once per wave, not per task, unless the wave mixes genuinely
different kinds of work. `askPerWave: false` skips the prompt and always takes `default`.

Carry the answer through the wave including re-delegations, **except** after a task has failed
once — then switch families deliberately and say why.

## Official plugins

Each non-Claude harness has a first-party Claude Code plugin giving background job control,
review commands and status/result/cancel. Same command shape across all three:

| Harness | Plugin | Commands |
| --- | --- | --- |
| codex | `openai/codex-plugin-cc` *(installed)* | `/codex:review`, `/codex:adversarial-review`, `/codex:rescue`, `/codex:status`, `/codex:result` |
| grok | `xai-org/grok-build-plugin-cc` *(installed)* | `/grok-build:delegate`, `/grok-build:critique`, `/grok-build:runs`, `/grok-build:show` |
| pi | `Agents365-ai/pi-plugin-cc` *(installed)* | `/pi:review`, `/pi:adversarial-review`, `/pi:rescue`, `/pi:parallel-rescue`, `/pi:status` |

`/pi:parallel-rescue` additionally needs pi-subagents, which `/pi:setup` reports as not
installed — the other `/pi:*` commands work without it.

Use the plugin commands for **reviews and background jobs** — they manage job ids and logs.
Use `run-role` when you specifically need one of *your* role definitions driving the model.

## Model diversity is the point

Re-delegating a failed task to the same model usually reproduces the same mistake: its
reasoning about the problem has not changed, and an amended brief mostly tells it to try harder
at what already failed. Switch families on the second attempt.

Same for verification — a reviewer from the family that wrote the code shares its blind spots.
Get the second opinion from a different family, and tell it to argue for refutation rather than
to "check". A reviewer asked to check agrees far too easily.

## Background runs

Anything longer than a one-file change goes in the background: a foreground run executes inside
a single tool call and dies with it. `run-role` on pi took over 4 minutes for a two-criterion
verification, so this is not a theoretical concern.

For plugin commands pass `--background` and never `--wait`. Job logs stream to disk as findings
arrive:

```
~/.claude/plugins/data/codex-openai-codex/state/<repo-slug>-<hash>/jobs/<job-id>.log
```

Job id from `/codex:status`; `/grok-build:show` prints `Log: <path>`. Read them incrementally —
`tail -n 80 <log>`, `grep -n "Review output" <log>` — never `cat` a whole review log into
context. Persist the finished review before triaging, then cite the file:

```bash
node "$CLAUDE_PLUGIN_ROOT/scripts/codex-companion.mjs" result <job-id> --json \
  > docs/reviews/wave-<N>-codex.json
```

`docs/reviews/` is gitignored and disposable — anything a reviewer or future maintainer must
see belongs in the spec or the PR description. Do not `git add -f` a review file. In a
worktree, run the review from inside it: the companion keys its state directory off the cwd.
