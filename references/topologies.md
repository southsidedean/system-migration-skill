# Migration shapes

Settle the shape in the first conversation. It changes the conflict rules and how results are stored.

## One-to-one

One source, one fresh destination. Same paths on both, so conflicts are rare. If the OS offers its own migration tool and the destination is fresh, mention it as an option: it may be simpler if the user wants everything. The phases here suit users who want to leave things behind or want proof.

## Many-to-one

Several sources into one new system.

- Inventory every source before copying any of them.
- Find conflicts: `python3 compare.py --conflicts source-a.tsv source-b.tsv source-c.tsv --output conflicts`. It lists paths where sources hold different content, and duplicates across sources.
- Agree on a rule before copying, and record it in `decisions.md`. Common options:
  - **Primary wins:** one source keeps the original paths, and the others go into `~/from-<source>/`.
  - **Newest wins:** only where it's safe, and never for config or credentials without review.
  - **Per-folder:** the user picks for each folder.
- Default to keeping both copies. Silent overwriting is the main risk in this shape.
- Copy and verify one source at a time, with a separate comparison for each.
- Record where every item came from in `decisions.md`.

Settings have just one winner on a machine. Have the user choose a primary for shell config, editor settings, and Dock or desktop layout, and show the differences for the rest.

## Absorbing a system later

The destination is already in use, and another system is being folded in.

- The destination has live data, so back it up first, and don't overwrite anything by default.
- Use `--ignore-existing`, or copy into `~/from-<source>/` and merge by hand.
- Take a destination inventory first as your baseline.
- Reuse the existing migration folder if there is one. Decisions from earlier sources are a useful starting point, but confirm them; don't assume they apply.

## Consolidation

Reducing several active systems to fewer, where each may stay in use until cut-over.

- Sources keep changing, so plan a final catch-up pass and a cut-over date.
- Find which system is the authority for each kind of data.
- Move services and scheduled jobs deliberately, so one job doesn't run in two places or none.
- Keep a source until the Phase 7 gate passes for that source.
