# Spec — What a fresh laptop needs

**Goal**: Close the two gaps an install audit found. A second machine should be able to install
this plugin and know exactly what else it needs, without a silent failure and without guessing.

## Findings this rests on

Verified on the reference machine, 2026-08-14:

| Fact | Evidence |
| --- | --- |
| `jq` is used in exactly one place | `skills/orchestrate/references/comms.md:45` — the only hit repo-wide |
| The three role files do the same job without it | they pipe to `python3 -c` instead |
| The doctor does not check `jq` | `grep -c jq scripts/orchestrator-doctor` → 0 |
| `codex` and `grok` live in `~/.local/bin`, `pi` in `/opt/homebrew/bin` | `which` |
| CLIProxyAPI is external to this repo | probed via `~/.claude/bin/cliproxy-run` and `~/.claude/cliproxy.key`, default `127.0.0.1:8317` (`scripts/orchestrator-harnesses:20-22`) |
| It is up on this machine | `GET :8317/v1/models` → 401 (auth required), not connection-refused |

A subtlety that must not be flattened: `run-role --harness codex` shells out to the **native
`codex` CLI**, not through CLIProxyAPI. CLIProxyAPI is what `orchestrator-harnesses` probes to
enumerate models, and what the companion plugins' own subagents use. Do not write documentation
that implies `run-role` requires it without establishing that first.

## Non-goals

- Shipping or vendoring CLIProxyAPI, `cliproxy-run`, or any harness CLI. They are separate
  projects with their own installers and credentials.
- Adding a `jq` check to the doctor. Removing the single use is strictly better than declaring a
  dependency we do not need.
- Turning the README into an install guide for other people's tools. It should say what is
  needed and point at the authority, not restate someone else's instructions that will drift.

## Acceptance criteria

1. **No `jq` anywhere in the repo's instructions.** `grep -rn "jq " --include="*.md" .` returns
   nothing outside `docs/reviews/`. The register snippet in
   `skills/orchestrate/references/comms.md` produces a working token with `jq` absent from
   `PATH`, proven by running it that way.
2. **The comms snippet stays consistent with the role files.** Same `python3 -c` form they use,
   so an agent reading either learns one idiom rather than two.
3. **README states the external prerequisites**: the three harness CLIs, which are not installed
   by this plugin, and CLIProxyAPI's role — including that it lives outside this repo and that
   `run-role` uses the native CLIs.
4. **Every command in that documentation is verified or absent.** No invented install commands.
   Where the true install path cannot be established from the machine or from upstream
   documentation, name the upstream project and link it rather than guessing a command. A wrong
   `brew install` line is worse than a link.
5. **The degraded state is stated plainly**: with no harness CLI installed, the plugin still
   works with `claude` alone, and `orchestrator-doctor` reports the others as warnings rather
   than failures. Someone should not think a fresh install is broken.
6. `tests/run-tests` still passes — 116 checks, 0 failed.

## Waves

### Wave 1 — both tasks, no shared files

**1a. Drop the `jq` dependency**
Scope: `skills/orchestrate/references/comms.md` only.
Replace `jq -r .token` with the same `python3 -c` extraction the three role files use. Change
nothing else in the file.
Done when: criteria 1 and 2 hold.

**1b. Document the external prerequisites**
Scope: `README.md` only.
Add a short prerequisites subsection covering the harness CLIs and CLIProxyAPI. Establish the
facts from the machine before writing; state the degraded-but-working baseline.
Done when: criteria 3, 4 and 5 hold.

## Verification plan

```bash
grep -rn "jq " --include="*.md" . | grep -v docs/reviews   # must be empty
PATH=/usr/bin:/bin <run the comms.md snippet against a scratch bus>   # jq absent, token still issued
tests/run-tests
```

## Rollback plan

Both are single-file, additive-to-documentation changes in one commit each. Reverting either
restores the current text exactly.

## Results

### Wave 1 — ACCEPTED

**1a — `jq` dropped.** `skills/orchestrate/references/comms.md` +1/-1: `jq -r .token` becomes
the same `python3 -c` extraction the three role files use. No `jq` remains in any instruction
file — the only hits left are in this spec, describing the problem. Verified live against a
scratch bus on 8497: the line issues a 22-character token and `/status` shows
`role: developer, harness: codex, model: gpt-5.6-sol`. Hiding `jq` from `PATH` became moot once
it is no longer invoked — the dependency is gone rather than satisfied.

**1b — prerequisites documented.** `README.md` +21/-0, placed directly under `## Harnesses` so
a reader meets it before the commands that assume it.

Every command was checked against this machine rather than taken on trust:

| Command | Evidence |
| --- | --- |
| `npm install -g @openai/codex` | `@openai/codex@0.147.0` present in npm globals |
| `curl -fsSL https://x.ai/cli/install.sh \| bash` | URL returns HTTP 200, `text/plain` |
| `npm install -g @earendil-works/pi-coding-agent` | `@earendil-works/pi-coding-agent@0.84.1` global; `pi` is its node script |
| `brew install cliproxyapi` | formula exists, stable 7.2.130, homepage matches the linked repo |

The `run-role` vs CLIProxyAPI distinction is stated correctly: the proxy serves the model list
for `orchestrator-harnesses` and the companion plugins' subagents, while `--harness codex`
shells out to the native CLI. The degraded baseline is explicit — a machine with none of it
installed is not broken.

`tests/run-tests`: 116 passed, 0 failed.

Note for anyone reproducing this machine: `codex` on `PATH` here resolves to a standalone
install (`~/.codex/packages/standalone/…`), not the npm one, though both are present. The npm
package is a legitimate way to obtain it, so the documented command stands.
