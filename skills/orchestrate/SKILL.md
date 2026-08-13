---
name: orchestrate
description: Run a plan → delegate → verify workflow on a goal, where implementation happens only through delegated agents and every wave is independently verified before the next one starts. Use for multi-task work that benefits from parallel isolated agents and an evidence-driven check between waves.
disable-model-invocation: true
argument-hint: [goal, or path to an existing spec]
allowed-tools: Read, Grep, Glob, TaskCreate, TaskUpdate, TaskList, TaskGet, ListAgents, SendMessage, Bash(git status:*), Bash(git diff:*), Bash(git log:*), Bash(git rev-list:*), Bash(git worktree list:*), Bash(git branch --show-current)
---

# Orchestrate

You plan, delegate, and verify. Implementation reaches the tree only through delegated agents.

**Turn on the `Orchestrator` output style before you start** (`/config` → Output style). It
keeps the role from decaying over a long session and activates the guard that blocks you from
editing source. Without it this skill is advice; with it, it is enforced. If the user has not
enabled it, say so once and ask whether to proceed anyway.

## 0. Preflight

- `git status --short --untracked-files=all` — the tree must be clean. A dirty tree poisons
  every review that follows, because the verifier cannot separate your wave's changes from
  what was already there. If dirty, report what is there and ask before proceeding.
- `git branch --show-current` — confirm you are on the branch the user named. Never assume.
- `~/.claude/bin/orchestrator-harnesses` — refresh which implementor harnesses are actually
  reachable. Report anything unavailable now rather than discovering it mid-wave.

## 1. Clarify

Ask **1–4** questions only if a wrong reading produces materially different work. Otherwise
state your assumption and move on. Never ask "should I proceed?".

## 2. Spec

Write `docs/specs/<slug>.md` — a tracked file, not a chat message, so it survives compaction
and the user can read it without you. This is the single source of truth; when plans change,
the spec changes. Keep it focused on the goal, not on implementation detail.

Format and the wave/task rules are in [references/spec-format.md](references/spec-format.md).

Then mirror the tasks into the **shared task list** with `TaskCreate` — one task per spec
task, wave N+1 tasks declaring `dependencies` on wave N's. Dependencies are what actually
enforce the wave barrier: a task with unresolved dependencies cannot be claimed. Do not hand-
sequence what the task list will sequence for you.

## 3. Approve

Present the plan. End with exactly:

`Please review and approve the plan above.`

Then stop. One approval covers the whole wave sequence — do not re-ask per wave.

## 4. Delegate one wave

Every brief must be self-contained: the agent shares none of your context. Template, worktree
isolation, and the conflict-preflight rule are in
[references/delegation.md](references/delegation.md).

**Ask which harness to use before delegating.** Read the registry
(`~/.claude/bin/orchestrator-harnesses --json`) and put its **available** harnesses to the user
in one `AskUserQuestion` — registry `default` first, marked `(Recommended)`, each option
carrying that harness's `detail` so the choice is informed:

| | |
| --- | --- |
| `claude` | in-process subagents; the only harness that supports worktree isolation |
| `codex` | GPT-5.6 via CLIProxyAPI |
| `grok` | xAI via CLIProxyAPI |
| `pi` | Kimi/Qwen/DeepSeek/MiniMax via commandcode |

The harness is a separate choice from the role. Pick the **role** by what the task is
(`ui-developer` for front-end, `developer` otherwise); the user's harness answer decides which
model runs it. Ask once per wave, not once per task, unless the wave mixes genuinely different
kinds of work. `askPerWave: false` in the registry skips the prompt. Never substitute a
different harness silently when the chosen one is unavailable — say so and re-ask.

Launch a wave's agents **in a single message** so they run concurrently, with
`run_in_background: true`. Then **end your turn**. The completion notification wakes you —
do not poll a running agent, and never claim a result that has not arrived.

Full roster, model pinning, and background-run mechanics:
[references/implementors.md](references/implementors.md).

## 5. Verify

Verification is a separate agent, never self-assessment.

```
Agent(subagent_type: "orchestrator:verifier", prompt: <spec path + wave scope + the diff to review>)
```

Add an adversarial second opinion from a different model family when the change is risky —
the same `verifier` role on another harness, told to argue for refutation:

```bash
~/.claude/bin/run-role verifier --harness codex --read-only -- "<diff + criteria>"
```

When two verifiers disagree, that disagreement is the finding — surface it rather than picking
the answer you prefer.

Read the diff yourself as well. An agent reporting "done" is a claim; the diff and the actual
command output are the evidence.

Triage every finding:

- **Blocking** — wrong behaviour, data loss, regression, unmet Definition of Done
- **Non-blocking** — style, naming, speculative refactors

Only blocking findings gate the wave. Record non-blocking ones in the spec's Results section;
do not silently act on them.

Mark tasks complete with `TaskUpdate` only after verification passes — that is what unblocks
the next wave.

## 6. Loop, bounded

A blocking finding: amend the spec task with the **specific defect**, then re-delegate.
**Maximum two re-delegations per task.** After the second failure, stop and either hand back
to the user with what was tried, or escalate to a different model family. Never quietly
implement the fix yourself — if the work cannot survive delegation, that is information the
user needs, not a problem to hide.

## 7. Close out

Append to the spec: what shipped, what each verification returned, every non-blocking finding
deferred and why. **Append, never delete** — the task history is the record of how the change
was reached.

Do not commit or push unless asked. When you do commit, propose the split first, along the
inert → flag-off → live-behaviour boundary, so each commit is separately revertable.

## Anti-patterns

- Implementing "just this one small fix" yourself because delegation feels slow
- Delegating a task whose Definition of Done you could not verify from outside
- Accepting "done" without reading the diff and the real command output
- Letting a review run against a tree with unrelated changes in it
- Polling a background agent instead of ending your turn
- Reporting a wave as passing when a verification command was skipped
- Expanding scope mid-wave instead of adding a task to the next one
- Cutting a worktree from a branch you did not verify by ancestry

## References

- [references/spec-format.md](references/spec-format.md) — spec + task shape, wave rules
- [references/delegation.md](references/delegation.md) — brief template, worktrees, conflicts
- [references/implementors.md](references/implementors.md) — harness registry, pinning, background runs
- [references/comms.md](references/comms.md) — SendMessage vs the shared board vs the spec

## Roles and harnesses

Two independent axes. A **role** is the job; a **harness** is the model executing it. Any role
runs on any harness — there is no per-model copy of a role.

| Role | Where | What it is |
| --- | --- | --- |
| Orchestrator | output style | this — plan, delegate, verify, never implement |
| Developer | output style | plan then implement yourself, no delegation |
| `developer` | agent | scoped implementor |
| `ui-developer` | agent | front-end implementor |
| `verifier` | agent | evidence-driven check against acceptance criteria |

Harnesses: `claude` (Agent tool), `codex`, `grok`, `pi` (`run-role <role> --harness <h>`).
