# Prompt for overnight agent
Feb. 18 2026

Do not modify any source files until AGENT_NOTES.md exists and contains both a project summary and a written implementation plan. Create AGENT_NOTES.md in the project root.

You are working autonomously. Follow these phases strictly:

PHASE 1 — UNDERSTAND
Read enough of the codebase to understand purpose, entry points, and main modules. Write a short summary in AGENT_NOTES.md covering: what the project does, its current structure, and the most important gaps or bugs you noticed. Limit the summary to the most important gaps; do not attempt to fix them in Phase 1. Do not modify any source files yet.

PHASE 2 — PLAN
Propose up to 5 improvements ranked by user-facing value. For each, estimate scope as small/medium/large. Scope guide: Small = one or two files, no new deps; Medium = a few files or one new dependency; Large = architectural or many files. Only proceed with small and medium items. Do not add large items to the plan. Append the plan to AGENT_NOTES.md. Do not start implementing until the plan section is written.

If an improvement would touch many more files than the scope suggests (e.g. "one or two files" but you find 10+), either narrow the change to the minimal set that meets the goal or note in the plan/Uncertain that you expanded scope and why.

PHASE 3 — IMPLEMENT
Implement each approved item one at a time. Do not start the next improvement until the current one is implemented, tested, and committed. Commit after each with a clear message. Do not refactor existing code unless it is directly blocking an improvement. Do not add new dependencies without noting them in AGENT_NOTES.md.

For optional features that depend on a heavy or sometimes-broken dependency, consider lazy import or runtime check so the rest of the app still runs when the dependency is missing; note in AGENT_NOTES if you do this.

PHASE 4 — TEST
Write tests for all new or modified behavior. Prefer tests that always run and pass or fail explicitly in the project's normal environment. If you use a skip (e.g. for an optional dependency), say so in Uncertain and why; prefer graceful degradation (test passes either way) where possible. Run the tests. Fix failures. Do not move on if tests are failing.

If a test cannot pass in this environment for reasons outside the code (e.g. missing or broken system library), note it in Uncertain, document the test's intent, and continue with the next improvement instead of blocking the run.

PHASE 5 — HANDOFF
Append a section to AGENT_NOTES.md titled "Manual Testing Checklist" with specific steps the developer should follow to verify the work looks correct from a user perspective. Also note anything you were uncertain about or left incomplete. In Uncertain, list any tests that skip or depend on a specific environment so the developer can decide whether to change or accept them.

Constraints:
- Stay within the existing tech stack; use the project's existing test runner and style (e.g. pytest); do not introduce a new test framework
- Do not delete or rename existing files without a strong reason (document if you do)
- If you are unsure whether something is in scope, skip it and note it
- Prefer simple, working solutions over clever ones
- When in doubt, do the minimal change that satisfies the plan and note the rest in Uncertain

