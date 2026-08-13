# Spec — Harness Control (ink redesign)

**Goal**: Replace the single-page dashboard with the ink app shell from the reference, so the
orchestrator's actual work — runs, stages, agents, verdicts — is visible while it happens.

## The gap that shapes this

The reference is not a reskin. Roughly half of what it shows does not exist yet:

| Reference shows | Today |
| --- | --- |
| Run #6842, title, 12m 34s, prior runs | no run concept at all |
| Intent → Coordinator → Implementors → Verifier → Complete | no stages |
| Pause control, Complete state | no run lifecycle — but pause is genuinely possible, see below |
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
- Agent-to-agent "12/12 online" scale. Real sessions run one to four agents; the roster shows
  what actually registered.

Success rate is **in** scope: it ships as a real fraction of closed runs from the first run
onward — `2/2` early, a percentage once there is enough history to mean anything. Never a
placeholder.

## Acceptance criteria

1. `GET /runs` returns real runs with id, title, state, stages and timings; empty list before
   any run exists.
2. A delegation started through `run-role` or the Agent tool appears as a run, advances through
   its stages, and ends in `complete` or `failed` with a real duration.
3. Registered agents carry role, harness, model and liveness — no invented online count.
3b. **Pause actually pauses.** `POST /runs/<id>/pause` sends `SIGSTOP` to the delegated
   process and `resume` sends `SIGCONT` — verified as a real freeze and clean resume, not a
   kill. The run records `paused`. Caveat to surface in the UI: a process frozen mid-request to
   a model API may have its socket time out during a long pause, so pausing is safe for a
   breather and risky for an hour. Say so at the control rather than in a docs footnote.
4. The dashboard renders the ink shell: sidebar, kanji-marked nav, hero with wash, flow card,
   balance enso, agent garden, activity feed, seal footer.
5. Every number on screen traces to an API field. No placeholder metrics anywhere.
6. Offline keeps last-known data and marks it stale; never-connected says so without inventing
   an age.
7. Both themes correct; no token defined only inside the dark block.
8. No horizontal body scroll at a true 320px viewport, achieved by layout.
8b. The orchestration view must look deliberate at **1 run, 2 agents and 4 messages** — the
   real density of a single-developer session, not the mockup's. That sparse state is what gets
   screenshotted for approval.
9. Inlined artwork adds **under 130KB** total to `ui/dashboard.html` (measured: 124KB).
10. `tests/run-tests` passes, including new coverage for the runs API.

## Constraints

- One self-contained `ui/dashboard.html`. Strict CSP: no external anything, all assets inlined.
- The bus stays dependency-free Python stdlib. No new packages.
- Run storage is a JSONL file beside the message board, gitignored, per channel.
- Backwards compatible: `/status`, `/read`, `/who`, `/mcp` keep working unchanged.
- **Artwork**: WebP with alpha, in `design/art/` — 124KB inlined, against 1.3MB as PNG. Alpha
  is required: the washes sit on both the paper and the ink ground, so a flattened image breaks
  one theme. Encoded with `cwebp -size 26000 -alpha_q 50`; a 58KB encode was indistinguishable
  side by side, so the smaller one wins.
- **Dark treatment**: `filter: invert(1) hue-rotate(180deg) saturate(.7) brightness(.85)`.
  Inverting alone flips hue and turns the blossoms cyan and the sun teal; the hue-rotate puts
  them back. Verified over both grounds. Do not ship a second dark asset — the filter is free.
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
Open a run when a role starts, record its PID so the bus can pause it, advance its stage, and
close it with the exit status. Must degrade silently — if the bus is down, the role still runs.
No new dependencies.
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
