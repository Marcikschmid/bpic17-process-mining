# scripts/

Entry points, one task each, grouped by pipeline stage. Run them from the
repository root with the project interpreter, for example
`.\.venv\Scripts\python.exe scripts/assess_model.py ...`. The order of a full run
is in [docs/REPRODUCE.md](../docs/REPRODUCE.md); how the stages connect is in
[docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md).

Naming: `discover_*` / `refine_*` build models, `assess_model` measures them,
`render_*` turn saved results into tables and figures, `verify_*` / `audit_*`
re-check saved results independently, `select_*` copy audited assets into `report/`.

## Setup and data

| Script | Task |
|---|---|
| `setup.ps1` | Create `.venv/`, install pinned packages, register the notebook kernel, install Graphviz |
| `setup_graphviz.py` | Install the official Windows Graphviz ZIP inside the project (`.tools/`) |
| `setup_bpmn_viewer.py` | Install the pinned bpmn-js viewer locally and verify its npm integrity |
| `check_setup.py` | Check imports, Graphviz rendering, plotting and the notebook kernel |
| `start_jupyter.ps1` | Start JupyterLab with the repository as workspace |
| `download_data.py` | Download the BPIC-17 log and verify the publisher's file hashes |
| `inspect_log.py` | Check the complete import and export a first-case preview |

## 3.2 Log statistics

| Script | Task |
|---|---|
| `analyze_log.py` | Statistics of the complete, unchanged log (all lifecycle states) |
| `render_log_statistics.py` | Tables and plots of the raw-log statistics |
| `verify_log_statistics.py` | Recompute the statistics with an independent XML reader |

## 3.3.1 Discovery baselines (completion projection, log C)

| Script | Task |
|---|---|
| `discover_models.py` | Inductive and Heuristics Miner; PNML and vector figures |
| `discover_alpha.py` | Classic Alpha Miner |
| `discover_heuristics_variants.py` | Native heuristics net and dependency-threshold sweep |
| `discover_genetic.py` | Budgeted, seeded Genetic Miner run |
| `genetic_budget.py` | Measured Genetic Miner cost and early-stop rule (no rerun) |
| `recover_genetic_export.py` | One-time lossless recovery of the Genetic net export |
| `export_miner_overview.py` | Actual miner settings and the parameter overview |

## 3.3.2 Quality gate

| Script | Task |
|---|---|
| `evaluate_models.py` | Baseline evaluation; `--prepare` builds the log C sequence cache |
| `render_evaluation.py`, `finalize_evaluation.py` | Tables/figures of the baseline evaluation |
| `assess_model.py` | Soundness and four quality dimensions for one model (`--cache` selects log C or A) |
| `audit_dead_transitions.py`, `audit_genetic_dead_transitions.py` | Exact dead-transition and replay-ceiling certificates |
| `render_model_comparison.py` | Comparison and soundness tables of all models |
| `render_metric_methods.py` | Measurement methods per quality criterion |
| `render_assessment_index.py` | Index of all assessment records (`results/assessment/README.md`) |
| `render_genetic_comparison.py` | Genetic run compared with the other models |
| `verify_evaluation.py`, `verify_genetic_trial.py` | Independent checks of evaluation and Genetic results |

## 3.3.3 Refinement before the event abstraction (archived model)

| Script | Task |
|---|---|
| `refine_model.py`, `refine_frequent.py` | IMf sweeps on the full log and on frequent variants |
| `accelerate_refinement.py` | Exact finite-state Align-ET with PM4Py cross-check |
| `export_refined_model.py` | Export the selected refined IMf model |
| `render_refinement.py`, `verify_refinement.py` | Refinement figures and provenance checks |
| `manual_edits.py`, `render_manual_edits.py` | Screen all 128 edit combinations; tables |

## 3.3.3 Event abstraction and final model (log A)

| Script | Task |
|---|---|
| `abstract_log.py` | Build log A and the evidence audit of the abstraction rules |
| `refine_abstracted.py` | IMf sweep on log A; select the base model |
| `manual_edits_abstracted.py` | Screen all 32 edit combinations of the base |
| `export_final_model.py` | Export the final model (PTML, PNML, BPMN, block structure, figures) |
| `holdout_check.py` | Train-only rediscovery and train/test replay for both pipelines |
| `compare_abstraction.py` | All models evaluated on one common log |
| `render_abstraction.py` | Report tables of the abstraction stage |

## 3.3.4 Decision mining

| Script | Task |
|---|---|
| `mine_decisions.py` | Align all cases, extract pre-decision data, train CART per XOR, guarded replay |
| `render_decision_stages.py` | Feature-stage comparison and tuning tables |
| `render_branch_probabilities.py` | Branch probabilities at every XOR (step 1) |
| `render_decisions.py` | Decision blocks, annotated BPMN, browser view, report panels |
| `verify_decisions.py` | Re-check every rule, the split and all raw-data snapshots |
| `export_signavio.py` | BPMN files for SAP Signavio, checked against the final net |

## Report selection

| Script | Task |
|---|---|
| `select_feedback_report.py` | Copy comparison, abstraction, edit and final-model assets |
| `select_decision_report.py` | Copy audited decision-mining assets |
| `select_genetic_report.py`, `select_miner_overview.py` | Copy Genetic and parameter appendix assets |

Each `select_*` script records source and SHA-256 of its copies in `docs/manifests/`.
