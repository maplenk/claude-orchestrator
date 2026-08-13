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
