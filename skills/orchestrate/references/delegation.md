# Delegation

## The brief

Every brief is self-contained. The agent shares **none** of your context — not the spec you
just wrote, not the user's clarifications, not what the previous wave learned. Anything you
leave out, it will invent.

```
## Task
<verbatim task body from the spec>

## Repo
<absolute path> — branch <name>

## Files in scope
<explicit paths>
Off-limits: <paths owned by sibling tasks running right now, and why>

## Constraints
<repo rules that must hold — behaviour parity, feature-flag gating, migration guards,
 tenant prefixes, framework/language version limits>

## Definition of Done
<the spec's checklist for this task>

## Coordination
Read the board before you start, and post there if scope changes under you:
  ~/.claude/bin/agent-board read --to <your role>
  ~/.claude/bin/agent-board post --from <your role> --to orchestrator "<message>"

## When finished
- Run: <exact verification commands>
- `git add` every file you changed. Do NOT commit, push, or branch.
- Report: files changed, commands run, their ACTUAL output, and anything you could not do.
- Post a one-line status to the board addressed to orchestrator.
```

The board lines matter most for `codex-`, `grok-` and `pi-` implementors: `SendMessage` cannot
reach them at all, so the board is the only way they can tell you something mid-run. See
[comms.md](comms.md).

Two failure modes to design against. **Underspecified scope** — the agent widens the change
because nothing told it where the edge was. **Missing constraints** — the agent writes correct
code that violates a repo rule it had no way to know about. Both are your fault, not its.

## Running a wave

Launch every task in a wave **in one message** so they run concurrently, each with
`run_in_background: true`. Then end your turn. The completion notifications wake you.

Never poll. Reading a running agent's output to see how it is doing costs you context and
tells you nothing you will not be told. Never state or predict a pending agent's result — wait
for it to arrive.

Against a **shared working tree**, run tasks sequentially: concurrent agents editing one
checkout will collide regardless of how cleanly you split the files, because they share an
index. With **one worktree per task**, a wave runs concurrently and safely.

## Worktree isolation

```
Agent(subagent_type: "orchestrator:developer", isolation: "worktree", prompt: <brief>)
~/.claude/bin/run-role developer --harness codex --worktree -- "<brief>"
```

Both are **opt-in**. Ask the user before a multi-task wave rather than choosing for them —
isolation decides where their work lands and what they have to merge afterwards.

`run-role --worktree` cuts `orchestrator/<role>-<pid>` from the current HEAD into
`.claude/orchestrator/worktrees/`, prints the base ref and SHA it cut from, and prints the
merge and removal commands. Review the branch before merging; remove the worktree after.

Each agent gets its own checkout and its own index. Three rules:

**Verify the base by ancestry, not by name.** A worktree is cut from the project's default
branch, not from whatever branch you are standing on. Before anything commits:

```bash
git rev-list --count <base>..<branch>
```

A worktree cut from the wrong lineage makes merge tasks silently resolve to no-ops — the most
expensive failure in this whole workflow, because it looks exactly like success.

**Uncommitted work does not propagate.** `git worktree add` checks out a *commit*. Staged-but-
uncommitted work is absent from every worktree you spawn afterwards, so a wave must be
committed before the next wave can build on it.

**The clean-tree precondition is per-worktree.** Check each one before its review, not just
the main checkout.

## Conflict preflight

Tell each agent which sibling tasks are running and which files they own. An agent that finds
it needs an off-limits file should report the overlap and stop, not edit it. That report is
useful — it means your wave split was wrong, and you want to know before the merge, not after.

Use `ListAgents` to see what is running and `SendMessage({to: <name>})` to steer an agent
mid-flight without losing its context. Re-spawning loses everything it has learned; a message
does not.

## Choosing the implementor

Match the role to the work, not to the session:

Pick the **role** by what the task is, then the **harness** by which model should run it —
they are separate choices.

| Work | Role |
| --- | --- |
| General scoped implementation | `developer` |
| Front-end, components, styling, a11y | `ui-developer` |
| Verification | `verifier` |

```
Agent(subagent_type: "orchestrator:developer", isolation: "worktree", prompt: <brief>)  # claude
~/.claude/bin/run-role developer --harness codex -- "<brief>"               # anything else
```

A second independent attempt is the *same role on a different harness*, not a different role.

After a task fails once, re-delegating to the *same* model usually reproduces the same
mistake — its reasoning about the problem has not changed. Switch families on the second
attempt. See [implementors.md](implementors.md).
