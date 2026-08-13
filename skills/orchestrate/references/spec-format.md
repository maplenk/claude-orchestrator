# Spec format

The spec lives at `docs/specs/<slug>.md` — a real tracked file. It is the source of truth, not
a chat message: it must be readable by the user, by every delegated agent, and by you after a
compaction has wiped the conversation.

Keep it about the **goal**, not the implementation. Implementation detail belongs in the task
bodies, where it can change without rewriting the plan.

## Sections

- **Goal** — one sentence, the user-visible outcome
- **Tasks** — grouped by wave, at the top so they are the first thing anyone reads
- **Acceptance Criteria** — testable checklist. No "should work", "properly", "as expected"
- **Non-goals** — what is explicitly out of scope
- **Assumptions** — mark uncertain ones "(confirm?)"
- **Constraints** — repo rules every implementor must honour (behaviour parity, flag gating,
  migration guards, tenant prefixes)
- **Verification Plan** — exact commands, with expected output
- **Rollback Plan** — how to revert safely, if relevant
- **Results** — appended after each wave: what passed, what was deferred, what failed

## Task shape

One block per task. Waves are `## Wave N` headings; tasks sit under them.

```markdown
### Task: <short title>

<what this task achieves, one or two sentences>

**Scope** — files and areas in scope, and explicitly what is off-limits
**Inputs** — spec sections, prior wave output, reference files
**Definition of Done** — specific, checkable completion criteria
**Verification** — the exact commands the implementor must run
```

Mirror each one into the shared task list with `TaskCreate`. The spec holds the *content*; the
task list holds the *state* and the dependency graph. Do not maintain status in both — the spec
records results after a wave, the task list tracks in-flight status.

## Splitting rules

A good task is:

- **Isolated** — no two tasks in the same wave touch the same file. This is the single
  constraint that makes parallel delegation safe; everything else is preference.
- **~30 minutes** of implementation
- **Independently verifiable** — it has its own Definition of Done that can be checked without
  reference to its siblings

A wave is a set of tasks that can all run against the same starting tree. Wave N+1 may depend
on wave N's output; tasks *within* a wave may not depend on each other. Express that in the
task list with `dependencies` — the barrier is then enforced rather than remembered.

If two tasks want the same file, they are one task. Splitting them produces a merge conflict
and two agents each convinced the other broke the build.

## On `@@@task` blocks

If you have used AO or Intent, their specs use `@@@task` fences that auto-convert into
trackable Task Notes with `intent://` links. That conversion is a feature of those apps'
note store. **Nothing converts them here** — in Claude Code they are inert text.

The native equivalent is the pair above: markdown task blocks in the spec for content, plus
`TaskCreate`/`TaskUpdate` for state and dependencies. That gets you the same thing the `@@@`
syntax was buying — individually addressable units with status and ordering — without a
format that silently does nothing outside the app that invented it.
