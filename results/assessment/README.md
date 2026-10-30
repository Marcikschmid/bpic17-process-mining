# Model assessment records

Each `<name>.json` is written by `scripts/assess_model.py` for one saved Petri net
(PNML, or PTML converted to PNML), always evaluated on the same full completion
projection `tmp/evaluation/projected_sequences.json` (31,509 cases, 475,306 events,
5,623 variants, 24 activities). Provenance keys hold the model path and SHA-256 of
the model, input cache, raw log and every implementation file plus the PM4Py
version; `headline` is a flat row; `soundness` holds the PM4Py WF-net check, the
complete-state-space classical verdict or an unboundedness witness, easy/relaxed
soundness and safeness from a bounded exploration, and a PM4Py Woflan cross-check;
`simplicity` and `token` hold PM4Py arc degree, own size, Extended Cardoso and
ECyM, and PM4Py token fitness, ETC precision and generalization. Bounded nets with
a reachable final marking additionally get `exact_replay`, `alignment_fitness`
(exact finite-state alignments, PM4Py formula, A* cross-check) and
`align_et_precision`; otherwise `finite_state_metrics` states why they are missing.
`<name>_diagnostics/` (optional, `--diagnostics`) holds conformance CSVs.
Regenerate this file with `.\.venv\Scripts\python.exe scripts/render_assessment_index.py`.

`n/c` = not computed (finite-state metric on an unbounded net, or no verdict).

## Assessed models (10)

| Record | Model file | State space | Sound | Woflan | Exact replay % | Token fitness | Alignment fitness | Token precision | Align-ET | Generalization | Arc degree | Nodes | Ext. Cardoso | ECyM | model_assessment.py |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `alpha_miner` | `results/alpha/alpha_miner.pnml` | unbounded (witness) | no (unbounded) | unsound | n/c | 0.4958 | n/c | 0.1259 | n/c | 0.9870 | 0.3920 | 49 | 34 | n/c | `4eb9d46b` |
| `final_model` | `results/final/final_model.pnml` | bounded, 86 states | yes | sound | 79.39 | invalid | 0.9751 | invalid | 0.6974 | invalid | 0.7188 | 92 | 51 | 145 | `4eb9d46b` |
| `genetic_miner` | `results/genetic/seed_20261025/models/genetic_miner.pnml` | unbounded (witness) | no (unbounded) | unsound | n/c | 0.7410 | n/c | 0.5970 | n/c | 0.9828 | 0.7755 | 76 | 43 | n/c | `4eb9d46b` |
| `heuristics_dep_0.5` | `results/heuristics/dep_0.5/model.pnml` | unbounded (witness) | no (unbounded) | unsound | n/c | 0.8334 | n/c | 0.9978 | n/c | 0.8550 | 0.4815 | 143 | 108 | n/c | `4eb9d46b` |
| `heuristics_dep_0.7` | `results/heuristics/dep_0.7/model.pnml` | unbounded (witness) | no (unbounded) | unsound | n/c | 0.8334 | n/c | 0.9978 | n/c | 0.8549 | 0.4815 | 143 | 108 | n/c | `4eb9d46b` |
| `heuristics_dep_0.9` | `results/heuristics/dep_0.9/model.pnml` | unbounded (witness) | no (unbounded) | unsound | n/c | 0.8390 | n/c | 0.9965 | n/c | 0.8366 | 0.4913 | 141 | 108 | n/c | `4eb9d46b` |
| `heuristics_dep_0.99` | `results/heuristics/dep_0.99/model.pnml` | unbounded (witness) | no (unbounded) | unsound | n/c | 0.8460 | n/c | 0.9963 | n/c | 0.9052 | 0.5041 | 124 | 93 | n/c | `4eb9d46b` |
| `heuristics_miner` | `results/models/heuristics_miner.pnml` | unbounded (witness) | no (unbounded) | unsound | n/c | 0.8334 | n/c | 0.9979 | n/c | 0.8611 | 0.4815 | 143 | 108 | n/c | `4eb9d46b` |
| `inductive_miner` | `results/models/inductive_miner.pnml` | bounded, 484 states | yes | sound | 100.00 | 1.0000 | 0.9998 | 0.2926 | 0.2926 | 0.9757 | 0.6170 | 87 | 47 | 1,552 | `4eb9d46b` |
| `refined_imf` | `results/refinement/final_model.pnml` | bounded, 187 states | yes | sound | 80.45 | 0.9875 | 0.9765 | 0.5952 | 0.5977 | 0.9912 | 0.7008 | 89 | 52 | 551 | `4eb9d46b` |

Current `src/model_assessment.py`: `4eb9d46b`.
Diagnostics folders: `final_model_diagnostics/`, `inductive_miner_diagnostics/`, `refined_imf_diagnostics/`.
