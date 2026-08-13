# Design brief — Orchestrator control plane

A dashboard for the `orchestrator` Claude Code plugin. Hand this to a designer or a design
tool; it describes what the screen must do, not how to build it.

## The one job

A developer has several AI agents — on different models — working on their codebase in parallel.
This screen answers, at a glance: **is my setup healthy, and what are the agents saying to each
other right now?**

It is glanced at repeatedly during a work session, often on a second monitor, not read once. It
is operated, not browsed. If someone has to hunt for whether something is broken, the design has
failed.

## Where it lives

Served at `http://127.0.0.1:8477/` by a local Python server. Localhost only, single user, no
auth, no accounts, no multi-tenancy. Desktop-first; it should still hold at 320px but nobody is
using this on a phone.

Hard technical constraints:

- **One self-contained HTML file.** A strict CSP blocks all external CSS, JS, fonts and images.
  No CDN, no webfonts, no icon library, no framework. System font stacks only. Anything visual
  must be CSS or inline SVG.
- **Both light and dark**, following the OS. Neither is the "real" one.
- Wide content scrolls inside its own container; the page body never scrolls sideways.
- Full keyboard operability with visible focus states; respects `prefers-reduced-motion`.

## The data

All of it comes from three local endpoints. **Nothing on screen may be invented** — if the API
does not return it, it does not exist.

`GET /status` — the whole picture in one call:

| Field | Meaning |
| --- | --- |
| `doctor.ok` | overall pass/fail |
| `doctor.checks[]` | `{name, status: ok\|warn\|fail, detail, fix, required}` — 19 of them today |
| `doctor.usableHarnesses[]` | which models can actually be delegated to |
| `harnesses{}` | `{label, model, runner, plugin, available, detail, notes}` per harness |
| `roles[]` | `developer`, `ui-developer`, `verifier` |
| `agents[]` | `{name, idle_s}` — who is registered right now |
| `channel` | the git branch; messages are scoped to it |
| `messageCount`, `cursor` | for the live feed |

`GET /read?since=<cursor>` — messages: `{ts, from, to, topic, msg, hops}`
`GET /who` — registered agents and idle time

## What must be on screen

In priority order — this is also roughly the reading order:

1. **Readiness.** One unmistakable answer. Derived from `doctor.ok` plus any `required` check
   that is failing. This is the thing someone glances at.
2. **What is wrong, and the command that fixes it.** Every non-passing check carries a `fix`
   string. That string is the most actionable thing on the page — it should be trivially
   copyable.
3. **Harnesses.** Which models are available, which model each runs, and the command to
   delegate to it.
4. **Live message feed.** Newest last, showing `from → to`, topic, and text. Polls every 3s
   using `cursor` so it appends rather than redraws.
5. **Registered agents** and how long each has been idle.

## The states to design

Real, all of them reachable today:

| State | What it looks like in data |
| --- | --- |
| **Healthy** | `doctor.ok: true`, all harnesses available — the common case |
| **Healthy with gaps** | `ok: true` but 2 warns. **This is the default first-run state.** |
| **Broken** | a `required` check with `status: fail` — e.g. tools not linked |
| **Degraded** | `doctor: null` — the doctor script isn't installed; everything else still works |
| **Offline** | the server is down. Must not go blank — say so, and say what to do |
| **Empty** | no messages, no agents. Normal before a wave starts, not an error |

**The warn/fail distinction is the crux of this design.** Optional gaps are the *normal* state
and must not read as alarm — a first run always shows two. But a required failure must be
impossible to miss. Two states, genuinely different weight, neither one shouting over the other.
Getting this wrong in either direction makes the page useless: cry wolf and it gets ignored;
under-state a failure and delegation silently breaks.

## Real content to design against

Use these verbatim — they are today's actual output, and they show the real length and texture:

```
ok    plugin hook manifests        no duplicate-hooks conflicts
ok    tools on ~/.claude/bin       all four linked
warn  Orchestrator output style    current: Default
      fix: /config -> Output style -> Orchestrator
warn  agent bus registered as MCP  not registered (REST still works)
      fix: claude mcp add agent-bus --transport http http://127.0.0.1:8477/mcp
ok    harness: grok                14 model(s) via CLIProxyAPI
ok    usable harnesses             claude, codex, grok, pi
```

Messages look like:

```
orchestrator → all      [scope]    app/auth.php is off-limits this wave
developer    → orchestrator        task 1 done; 2 tests red in OrderReportTest
verifier     → all      [verdict]  NOT APPROVED: criterion 3 unmapped
```

Note the shapes: check names run to ~28 characters, `fix` strings are long shell/slash commands
that will wrap, messages are one or two lines, and `to` is either a role name or `all`.

## What good looks like here

- Summary before detail. The answer first, the evidence under it.
- State encoded in **form as well as text** — a chip, a stripe, a weight — so severity survives
  a glance and does not depend on reading.
- Semantic status color (ok / warn / fail) kept **separate from the accent hue**, so "this is
  interactive" and "this is fine" never get confused.
- Commands are unmistakably commands, and obviously copyable.
- Digits that sit in columns line up.
- Quiet when everything is fine. The healthy state is the one people see most; it should feel
  calm, not like a cockpit.

## Anti-patterns for this page

- A large hero. This is a tool; the top of the page should already be working.
- Optional warnings styled as errors — the first-run state would look broken when it is not.
- Decorative numbering. Nothing here is a sequence; only the *install* flow is, and that lives
  in a different document.
- Generic dashboard chrome — sidebar, breadcrumbs, avatar menu. There is one screen and one
  user.
- Emoji as status markers.
- Inventing metrics. No sparklines of things the API does not measure, no fake uptime, no
  progress bars over unknown durations.

## Deliverable

A single self-contained `ui/dashboard.html`. It gets served as-is — there is no build step and
no place for assets to live.

## Context, if useful

The plugin's premise: **roles and harnesses are orthogonal.** A role is the job (`developer`,
`ui-developer`, `verifier`); a harness is the model executing it (`claude`, `codex`, `grok`,
`pi`). The same role definition runs on any of them. The dashboard is where that matrix becomes
visible — which roles exist, which models can run them, and what they are currently saying.
