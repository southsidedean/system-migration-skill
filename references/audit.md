# Phase 6: Independent audit

Earlier checks were done by whoever did the work. An audit tests that work, so it should not start from their conclusions.

## Running it

Use a subagent if your environment has them, and tell the user that this may take a long time and use significant tokens. If not, start a fresh session with only the brief below.

Give the auditor:
- The user's original requirements, in their words, and `decisions.md`
- Machine names and how to reach them
- The read-only rules, and a single writable work folder
- A rule to report paths, sizes, and counts, never contents or secrets
- A rule not to trigger permission prompts, and to record blocked paths as not audited
- Instructions to read `status.md` and the runbook only **after** forming results, and then to test their claims

Don't give it your findings or tell it what you expect.

Use separate auditors for separate questions:
1. **Completeness:** every file, app, package, and setting, source against destination.
2. **Sensitive data:** content search across every machine, plus full verification of every archive, member by member.

## What it should do

- Hash everything on each machine, and compare everything. No sampling.
- Reconcile counts: total files must equal the sum of all classes.
- Prove its tools with known-answer fixtures and hostile file names, and run positive controls.
- State coverage: files in scope, files checked, exclusions, and NOT AUDITED.
- Rank findings by what would be lost if the source were erased today.
- List false or stale doc claims, and separate facts from inferences.

## Handling results

Auditors make mistakes too, and their inventories go stale as the machines change. Before relaying a major finding, check it directly, and tell the user about any finding that turned out to be wrong or out of date. Then:

1. Report to the user: what would be lost, what looks wrong, and what can't be verified.
2. Get decisions, record them, and fix what they approve.
3. Fix the docs in one pass, and re-verify what changed.

If an auditor changed anything or prompted the user despite its instructions, tell the user exactly what changed and how to undo it.
