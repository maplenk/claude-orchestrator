# Spec — Run provenance (closing wave 3's two failures)

**Goal**: Make a run record its progress and make an agent record what it is running on, so
`docs/reviews/wave3-verification.md` criteria 2 and 3 hold on evidence rather than on the
dashboard deriving them from elsewhere.

## What is actually broken

Neither failure is in the bus. `scripts/agent-bus` already accepts, stores and serves all of
it — `op_register` takes `role`/`harness`/`model` (line 192), `op_run_stage` appends stages in
order (line 351), and a hand-rolled curl registration renders correctly. The producers never
send it.

| Criterion | Symptom | Cause |
| --- | --- | --- |
| 2 — a run advances through its stages | 7 of 60 runs carry any stage; those that do carry exactly one | `run-role` calls `stage_run running` once (line 244) and nothing else. `close` sets state but appends no stage. |
| 3 — agents carry role, harness, model | `harness` and `model` are `null` on every real agent | The three role files register with `{"name": "<your role>"}` only. `run-role` never registers, and never tells the agent what it is running on. |

`role` is populated today only because a role's name and its role happen to coincide. That is
a coincidence, not a mechanism.

### The ordering problem this turns on

The agent is the only party that knows what it is doing mid-run, so it must be able to stage
its own run — which means it needs the run id in its environment. But `run_harness` launches
the child *before* it opens the run, because `op_run_open` wants the harness pid and bash
cannot know a child's pid before starting it. A variable exported after the child starts is
not inherited.

So the run must be opened *before* the launch, and the pid attached *after*. That needs one
small addition to the bus. Everything else follows from it.

Rejected alternative: passing the run id through a temp file whose path is exported ahead of
the launch. No bus change, but the child can read the file before the parent writes it, and a
race in the identity path is worse than an endpoint.

## Non-goals

- Inventing intermediate stages inside `run-role`. A bash wrapper cannot see what a model is
  doing; anything it emits between launch and exit would be decoration. The wrapper records
  only what it genuinely observes — launch, and outcome.
- Detecting the agent's "first write" by tapping stdout or watching the filesystem. Piping the
  harness's output to detect activity risks its exit-code propagation, which is load-bearing.
- Changing the dashboard. It already renders `run.stages` (`ui/dashboard.html:1051`) and the
  agent's harness and model. Both go from empty to populated with no UI change; if either
  still reads wrong afterwards, that is a new finding, not this spec.
- Backfilling the 60 existing runs. History stays as it was recorded.

## Acceptance criteria

1. **`POST /runs/<id>/pid` attaches a pid to an open run.** Returns the updated run; refuses a
   closed run, a non-integer pid, and an unknown id, with the same error shape as the existing
   run ops. Pause works against a pid attached this way — verified as a real `SIGSTOP` freeze,
   not merely a state change.
2. **Every `run-role` delegation records at least two stages, ending in a terminal one.**
   `running` at launch, then `complete` or `failed` recorded *before* the close event. This
   must hold for every harness, including the `pi --read-only` branch.
   Note for the implementor: `op_run_stage` rejects a run already in `complete`/`failed`
   (line 359), so the terminal stage is recorded before `close_run`, never after.
3. **A delegation that never launches records `blocked`.** `fail_run` — unknown harness, `pi`
   not on PATH, `--read-only` on a harness that cannot enforce it — opens a run, stages
   `blocked`, and closes `failed` with the real exit code.
4. **`run-role` exports the run's identity to the harness**: `ORCHESTRATOR_RUN_ID`,
   `ORCHESTRATOR_ROLE`, `ORCHESTRATOR_HARNESS`, `ORCHESTRATOR_MODEL`, `ORCHESTRATOR_BUS`, all
   set before the child starts. `ORCHESTRATOR_DELEGATE` keeps its current value and meaning —
   `hooks/orchestrator-guard.py:91` depends on it.
   `ORCHESTRATOR_MODEL` is empty when the harness is using its own default; empty means
   unknown and must never be filled with a guess.
5. **A registered agent from a real delegation carries role, harness and model.** `GET /who`
   and `/status` show them non-null for an agent registered by a headless harness under
   `run-role`. Registration reads the exported environment; it does not ask the model to
   recall what it is running on.
6. **A Claude-harness agent registers with what it actually knows.** `harness: "claude"` and
   its role; `model` omitted rather than guessed. An omitted model must render as unknown, not
   as a fabricated one.
7. **The agent stages its own run.** Each role file instructs the agent to stage at least
   twice during real work, using the fixed vocabulary below, and to skip staging silently when
   `ORCHESTRATOR_RUN_ID` is unset (the Agent-tool path, where there is no run).
8. **Degradation is unchanged.** With the bus stopped, `run-role` still runs the harness, still
   returns its exit code, and prints nothing extra. Every new call is best-effort on the
   existing 1s-timeout `bus_post`.
9. **`tests/run-tests` passes**, with new coverage for the pid endpoint, the stage bracket, the
   `blocked` path, and the exported environment. Coverage must assert behaviour, not the
   presence of a string in a script — the fifteen vacuous guard tests in this repo's history are
   the standing example of what does not count.
10. **A live delegation shows the whole chain.** One real `run-role` invocation produces a run
    whose stages read as a progression, with an agent-emitted stage among them, and an agent in
    the roster carrying its harness and model.

### Stage vocabulary

Fixed, so the dashboard's stage list stays legible across roles:

| Emitter | Stages |
| --- | --- |
| `run-role` | `running`, then `complete` / `failed` / `blocked` |
| developer, ui-developer | `understanding`, `implementing`, `verifying` |
| verifier | `understanding`, `checking`, `reporting` |

Criterion 10 is the one that depends on a model following an instruction. Criteria 2 and 3 are
the mechanical floor and hold regardless — that split is deliberate, so a model that ignores
the instruction degrades the record rather than breaking it.

## Waves

### Wave 1 — the bus op

**1a. Attach-pid endpoint in `scripts/agent-bus`**
Scope: `scripts/agent-bus` only.
Add `op_run_pid(id, pid)` reusing `_parse_pid` and `_get_run`, a `pid` event folded by
`_apply_run_event`, the `POST /runs/<id>/pid` route, an entry in the ops dict (~line 530), and
the matching MCP tool alongside `run_open`/`run_stage`. Refuse on a closed run.
Done when: criterion 1 holds and all existing tests still pass.

### Wave 2 — the producers

Depends on wave 1 at runtime. Two tasks, no shared files.

**2a. Stage bracket and identity export in `scripts/run-role`**
Scope: `scripts/run-role` only.
Open the run before launching the child so the run id can be exported; attach the pid after.
Add the terminal stage before close, `blocked` in `fail_run`, and the five exported variables.
Keep every bus call best-effort.
Done when: criteria 2, 3, 4 and 8 hold.

**2b. Registration and staging in the role instructions**
Scope: `agents/developer.md`, `agents/ui-developer.md`, `agents/verifier.md`,
`skills/orchestrate/references/comms.md`.
Update the register snippet to send role, harness and model from the exported environment, and
add a one-line staging instruction using the vocabulary above. State that unset
`ORCHESTRATOR_RUN_ID` means skip staging without comment. Say what the Claude-harness path
sends instead (criterion 6). Keep these sections as short as they are now — they compete for a
model's attention with the actual brief.
Done when: criteria 5, 6 and 7 hold.

### Wave 3 — tests

**3a. Coverage in `tests/run-tests`**
Scope: `tests/run-tests` only.
Cover criterion 1's endpoint including its refusals, the stage bracket end to end, the
`blocked` path, and the exported environment observed from inside a delegation. Assert
behaviour, not script contents.
Done when: criterion 9 holds and the suite is green.

### Wave 4 — verification

Independent verifier on a harness that did not build waves 1–3, against these criteria.
Saved to `docs/reviews/run-provenance-verification.md`. Wave 3 of the previous spec was cut
short mid-review; this one runs to completion before anything is called done.

## Verification plan

```bash
tests/run-tests                                   # must stay green throughout
~/.claude/bin/orchestrator-doctor                 # guard still enforcing

# criterion 2, 3, 4, 10 — a real delegation, end to end
~/.claude/bin/run-role developer --harness pi -- "noop: register, stage, exit"
curl -s http://127.0.0.1:8477/runs | python3 -m json.tool | tail -40
curl -s http://127.0.0.1:8477/who  | python3 -m json.tool

# criterion 3 — a run that never launches
~/.claude/bin/run-role developer --harness nosuch -- "x"; echo "exit=$?"

# criterion 8 — bus down
pkill -f agent-bus; ~/.claude/bin/run-role developer --harness pi -- "noop"; echo "exit=$?"
```

## Rollback plan

Wave 1 is additive — an unused endpoint is inert. Wave 2 is the only behavioural change and is
its own commit; reverting it returns `run-role` to a single stage and null harness/model,
which is exactly today's state. Wave 3 is tests. Each wave is its own commit.

## Results

_Appended after each wave._

### Wave 1 — `POST /runs/<id>/pid` — ACCEPTED

`scripts/agent-bus`, +34/-3. `op_run_pid` reuses `_parse_pid` and `_get_run`, appends a `pid`
event, and is wired into `_apply_run_event`, the HTTP route table, the ops dict and the MCP
tool list.

Verified by a second agent's script, re-run by the orchestrator on port 8483:

- **C1** — `pid` absent at open, `50096` after attach, same in `GET /runs`.
- **C2 — a real freeze.** Tick lines `3 → 3 → 3` across a 2.0s pause; `ps` state `Ts`. After
  resume: 13 lines (+10) and `Ss`. Not a state flip.
- **C3** — six refusals (unknown id, non-integer pid, float string, missing, null, closed run),
  each with a sensible error and the runs JSONL byte-identical at 715 bytes throughout.
- **C4** — pid `50096` still present after stopping the bus and starting a new one against the
  same JSONL.
- **C5** — `tests/run-tests`: 88 passed, 0 failed, matching the pre-change baseline.

Noted, not a defect: errors return HTTP 200 with an `{"error": ...}` body. That is this bus's
existing convention (`op_run_stage` behaves the same), and the criterion asked for consistency
with it.

Process note: the implementing agent went idle twice without reporting evidence. The diff was
sound, so it was kept and verified independently rather than re-run.

### Wave 2 — the producers — ACCEPTED

`scripts/run-role` +62/-25; `agents/{developer,ui-developer,verifier}.md` +13/-8 each;
`skills/orchestrate/references/comms.md` +14/-5.

The clearest evidence is a differential runs JSONL, old `run-role` against new, on one bus:

```
old  {"id":"99c4ad","event":"opened",...,"pid":61765}
     {"id":"99c4ad","event":"stage","stage":"running"}
     {"id":"99c4ad","event":"closed","outcome":"complete"}          <- one stage, no terminal

new  {"id":"22fc2b","event":"opened",...}                            <- no pid at open
     {"id":"22fc2b","event":"pid","pid":61844}                       <- attached after launch
     {"id":"22fc2b","event":"stage","stage":"running"}
     {"id":"22fc2b","event":"stage","stage":"complete"}              <- terminal stage, before close
     {"id":"22fc2b","event":"closed","outcome":"complete"}
```

- **Stage bracket** — success gives `running` → `complete`; failure gives `running` → `failed`
  with the harness's real exit code (42 in the probe). The terminal stage is ordered before the
  close event in the JSONL, so it is not being silently rejected.
- **`blocked`** — unknown harness (exit 64), the `claude` pointer (64), `pi` absent (69), and
  the `--read-only` refusal (64) each record `blocked` then close `failed`.
- **Environment** — the child saw all five variables; `ORCHESTRATOR_DELEGATE=developer`
  unchanged. With no model resolved, `ORCHESTRATOR_MODEL=` empty and no `-c model=` in argv —
  empty rather than wrong, as specified.
- **Bus down** — argv SHA identical to the old script (`00c17c26…`), stderr identical, exit
  codes 0 and 7 propagated, `ORCHESTRATOR_RUN_ID=` empty.
- **`pi` refactor** — argv identical old vs new: `ARGC=12` including `--tools read` under
  `--read-only`, `ARGC=10` without. Behaviour-preserving.
- **Pause attaches the right pid** — the fake harness recorded its own pid as `76732`; the run's
  `pid` event is `76732`. Not the wrapper's. This was the risk worth chasing: had `run-role`
  attached its own pid, pause would freeze the wrapper while the harness ran on, and every
  other number would still have looked correct.
- **Snippets** — all four extracted verbatim from the docs (0-byte diffs) and run against a live
  bus; registrations and `implementing`/`checking` stages both landed.
- `tests/run-tests`: 88 passed, 0 failed.

Honest limit on the end-to-end pause: explicit before/after tick counts were not captured. What
is on record is the pid identity above, `paused` → `resumed` two seconds apart, and 16 ticks
across roughly four seconds of wall clock where an unfrozen 10/s ticker would have produced
about forty. Together with wave 1's direct freeze proof (`3 → 3 → 3`, `ps` state `Ts`) that is
sufficient, but it is inference rather than a fourth direct observation.

Unrequested change, kept: the agent consolidated the `pi` branch into one `PI_ARGS` array. The
old code called `run_harness` with `--tools read` and then again without it, working only
because `run_harness` exits — a read-only delegation was one edit away from running writable.
Verified behaviour-preserving above.

### Wave 3 — tests — ACCEPTED

`tests/run-tests` +292/-0, purely additive: **88 → 116 checks**, green twice consecutively, no
stray bus left on the test port. No existing check weakened or removed.

The tests read behaviour, not script text: a fake harness is launched by `run-role` with a
deliberately minimal environment, so any `ORCHESTRATOR_*` it reports can only have come from
`run-role`. `run.pid` is asserted equal to the pid the harness reported for itself. Freezes are
asserted by sampling file size six times and requiring every sample identical, after first
observing the writer alive — a freeze assertion over an already-dead process would otherwise
pass for the wrong reason. `AGENT_BUS_PORT` is pinned so the suite can never post fixtures into
a live session's bus.

### Wave 4 — verification — ACCEPTED

Full record: `docs/reviews/run-provenance-verification.md`.

Both originally-failed criteria hold. A live delegation records five stages
(`running → understanding → implementing → verifying → complete`); `/status` shows
`role/harness/model` populated.

Mutation testing answered the question the pass count could not: against the old `run-role`,
8 of the new checks go red, with `'stages': [{'stage': 'running'}]` and `'stages': []` in the
failure detail — the original defect reproduced. Against the old `agent-bus`, the suite aborts
at the pid call with a 404, proving those checks depend on the new endpoint. No new check was
found passing against an old implementation.

Standing gap: every stage progression on record came from a fake harness executing the snippet
deterministically. The mechanism is proven; a real model's compliance with the staging
instruction is not, and cannot be until real delegations run.
