# results/

Generated outputs, one folder per pipeline stage. Everything here is written by
`scripts/` and can be regenerated ([docs/REPRODUCE.md](../docs/REPRODUCE.md)).
JSON records carry input and implementation hashes for provenance.

**Current final model:** [`final/`](final/) (event abstraction + IMf + edit R1;
85.35 % exact whole-case replay, Align-ET 0.826, 56 nodes), its decisions in
[`decision_mining/`](decision_mining/) and its Signavio files in [`signavio/`](signavio/).

| Folder | Stage | Content |
|---|---|---|
| [`tables/`](tables/) | 3.2, 3.3.1 | Raw-log statistics, import summary, discovery manifest, baseline evaluation |
| [`figures/`](figures/) | 3.2, 3.3.1 | Raw-log plots and the IM/HM baseline model figures |
| [`models/`](models/) | 3.3.1 | Inductive and Heuristics Miner Petri nets (PNML) |
| [`alpha/`](alpha/), [`heuristics/`](heuristics/), [`genetic/`](genetic/) | 3.3.1 | Further baselines: Alpha, native heuristics net + sweep, seeded Genetic run |
| [`parameters/`](parameters/) | 3.3.1 | Miner parameter overview (PDF, JSON, TeX) |
| [`assessment/`](assessment/) | 3.3.2 | One quality/soundness record per model, conformance diagnostics ([index](assessment/README.md)) |
| [`comparison/`](comparison/) | 3.3.2 | Cross-model comparison, soundness summary, measurement methods, hold-out check |
| [`refinement/`](refinement/) | 3.3.3 (before abstraction) | 40 IMf candidates and the refined IMf model |
| [`manual_edits/`](manual_edits/) | 3.3.3 (before abstraction) | Screen of 128 edit combinations on the refined IMf model |
| [`before_abstraction/`](before_abstraction/) | 3.3.3 (archived) | Earlier final model with its assessment, decisions and Signavio files ([README](before_abstraction/README.md)) |
| [`abstraction/`](abstraction/) | 3.3.3 (final) | Abstraction audit, IMf sweep on log A, edit screen, common-log comparison |
| [`final/`](final/) | 3.3.3 (final) | Final model: PTML, PNML, BPMN 2.0, block structure, figures, manifest |
| [`decision_mining/`](decision_mining/) | 3.3.4 | Branch probabilities, CART rules per XOR, annotated BPMN, audits |
| [`signavio/`](signavio/) | 3.3.4 | BPMN files for SAP Signavio (probabilities and rules) |

Not in Git: `runs/` (local run logs) and `decision_mining/observations/`
(per-decision training rows; regenerate with `scripts/mine_decisions.py`).
Report copies of selected files live in `report/tables/` and `report/figures/`.
