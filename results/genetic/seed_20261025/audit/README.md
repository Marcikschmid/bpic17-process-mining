# Historical export audit

`INVALID_duplicate_ids.pnml` and `INVALID_export_evaluation.json` preserve an
invalid first export and its invalid measurements. **Do not use these scores.**
The native converter gave 15 silent transitions the same empty name, which was
exported as repeated PNML IDs. The prior name-only signature did not detect the
changed arc endpoints after import.

`original_graph.gv` was written from the native model before importing PNML.
It preserves unique object IDs, every unit-weight arc, visible labels and both
markings. `scripts/recover_genetic_export.py` reconstructs that exact graph with
unique identifiers; `scripts/verify_genetic_trial.py` independently checks all
edges, labels, markings and hashes. Corrected results are in `../manifest.json`.
Their replay reproduces the native evolutionary objective exactly, difference 0.

`historical_runner.py` matches its checksum in the original run manifest.
`historical_exporter.py` is the shared exporter from commit 214dc69. These are
archival source snapshots, not entry points to run. The live shared exporter
now assigns unique PNML identifiers in a model copy and has a regression test.
