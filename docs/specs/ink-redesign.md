# Spec — Harness Control (ink redesign)

**Goal**: Replace the single-page dashboard with the ink app shell from the reference, so the
orchestrator's actual work — runs, stages, agents, verdicts — is visible while it happens.

## The gap that shapes this

The reference is not a reskin. Roughly half of what it shows does not exist yet:

| Reference shows | Today |
| --- | --- |
| Run #6842, title, 12m 34s, prior runs | no run concept at all |
| Intent → Coordinator → Implementors → Verifier → Complete | no stages |
| Pause control, Complete state | no run lifecycle |
| Success rate 98.6% | no outcome history |
| Agents Online 12/12, per-agent model and role | `{name, idle_s}` only |
| Workspaces, Repositories, Audit Log | not concepts in this tool |

So this is a **backend wave first, then a UI wave**. Building the UI first would mean inventing
numbers, which the design brief explicitly forbids and which makes the page untrustworthy at
exactly the moment you need it.

## Non-goals

- Workspaces, Repositories and Settings views. Nav entries render disabled with a one-line
  "not yet" rather than being faked.
- Multi-user anything. One machine, one user, no auth. The greeting is local and cosmetic.
- Success rate until there is real outcome history to compute it from. It appears in wave 3
  or not at all — never as a placeholder number.

## Acceptance criteria

1. `GET /runs` returns real runs with id, title, state, stages and timings; empty list before
   any run exists.
2. A delegation started through `run-role` or the Agent tool appears as a run, advances through
   its stages, and ends in `complete` or `failed` with a real duration.
3. Registered agents carry role, harness, model and liveness — no invented online count.
4. The dashboard renders the ink shell: sidebar, kanji-marked nav, hero with wash, flow card,
   balance enso, agent garden, activity feed, seal footer.
5. Every number on screen traces to an API field. No placeholder metrics anywhere.
6. Offline keeps last-known data and marks it stale; never-connected says so without inventing
   an age.
7. Both themes correct; no token defined only inside the dark block.
8. No horizontal body scroll at a true 320px viewport, achieved by layout.
9. Inlined artwork adds **under 120KB** total to `ui/dashboard.html`.
10. `tests/run-tests` passes, including new coverage for the runs API.

## Constraints

- One self-contained `ui/dashboard.html`. Strict CSP: no external anything, all assets inlined.
- The bus stays dependency-free Python stdlib. No new packages.
- Run storage is a JSONL file beside the message board, gitignored, per channel.
- Backwards compatible: `/status`, `/read`, `/who`, `/mcp` keep working unchanged.
- **Artwork**: JPEG at ~q72 with a CSS mask for the fade, not PNG alpha — measured at 71KB
  inlined versus 1.3MB as PNG. Sources in `design/art/`.
- **Vendor marks**: use plain wordmarks. `design/artwork-and-marks.md` notes several vendors
  forbid the rounded-square badge treatment the reference uses, and that a wordmark is always
  safe. Ship `TRADEMARKS.md` with the nominative-use statement.

## Waves

### Wave 1 — data foundation

Tasks touch different files and can run concurrently, each in its own worktree.

**1a. Run registry in `scripts/agent-bus`**
Scope: `scripts/agent-bus` only.
Add a run concept: `POST /runs` to open one, `POST /runs/<id>/stage` to advance, `POST
/runs/<id>/close` to finish, `GET /runs` to list. Persist to
`.claude/orchestrator/runs/<channel>.jsonl`. Extend `register` so an agent may declare `role`,
`harness` and `model`; keep the existing token/identity rules exactly. Surface `runs` and the
richer `agents` in `/status`. Expose the same operations as MCP tools.
Done when: a run can be opened, advanced through stages, closed, and read back with real
timings; existing endpoints and all current tests still pass.

**1b. Emit run events from `scripts/run-role`**
Scope: `scripts/run-role` only.
Open a run when a role starts, advance its stage, close it with the exit status. Must degrade
silently — if the bus is down, the role still runs. No new dependencies.
Done when: `run-role … --harness pi` produces a run visible in `GET /runs`, and still works
with the bus stopped.

### Wave 2 — the shell and the orchestration view

Depends on wave 1. One task, because it is one file.

**2a. Ink shell + orchestration view in `ui/dashboard.html`**
Scope: `ui/dashboard.html` only.
Translate `design/Orchestrator Control Plane ink.dc.html` to vanilla JS against the live API.
Strip all canvas templating. Sidebar, nav, hero, flow card, balance enso, checks, agent garden,
activity, seal footer. Inline the artwork from `design/art/` within the size budget.
Done when: acceptance criteria 4–9 hold, verified in a browser.

### Wave 3 — verification and close-out

**3a. Independent verification** — `verifier` role on a different harness than built wave 2,
against these acceptance criteria.
**3b. Tests** — extend `tests/run-tests` to cover the runs API and the agent roster.

## Verification plan

```bash
tests/run-tests                                  # must stay green throughout
~/.claude/bin/orchestrator-doctor                # guard must still report enforcing
curl -s http://127.0.0.1:8477/runs | head -c 400
~/.claude/bin/run-role developer --harness pi -- "noop" && curl -s .../runs   # run appears
```
Plus a browser pass: both themes, a true 320px viewport, and the offline path with the bus down.

## Rollback plan

Each wave is its own branch and its own commit. `ui/dashboard.html` is replaced wholesale, so
reverting wave 2 restores the terminal dashboard exactly. Wave 1 is additive — the new
endpoints can be left in place unused, or reverted independently.

## Results

_Appended after each wave._
