# Reproduce the analyses

All commands run from the repository root in PowerShell and use the project
interpreter `.\.venv\Scripts\python.exe` (abbreviated `py` below; activation of
the environment is not needed). Analysis scripts write only to `results/` and
the ignored `tmp/`; they never overwrite report sources. How the stages depend on
each other: [ARCHITECTURE.md](ARCHITECTURE.md).

```powershell
Set-Alias py .\.venv\Scripts\python.exe   # this session only; shadows the Windows py launcher
```

## 0. Setup and data

Prerequisites: Git and Python 3.12 (`python` on PATH). Validated on Windows;
other platforms need their own Graphviz/dependency setup. Full-log processing
needs several GB of memory; some optimal-alignment runs take long.

```powershell
git clone https://github.com/Marcikschmid/bpic17-process-mining.git
Set-Location bpic17-process-mining
.\scripts\setup.ps1
py scripts/download_data.py
py scripts/check_setup.py
```

Build the completion-projection cache (log C), required by every later stage:

```powershell
py scripts/evaluate_models.py --prepare
```

## 1. Log statistics (3.2)

```powershell
py scripts/analyze_log.py
py scripts/render_log_statistics.py
py scripts/verify_log_statistics.py
```

## 2. Discovery baselines (3.3.1, log C)

```powershell
py scripts/discover_models.py
py scripts/discover_alpha.py
py scripts/discover_heuristics_variants.py
py scripts/discover_genetic.py
py scripts/render_genetic_comparison.py
py scripts/export_miner_overview.py
```

The Genetic Miner may stop early; seeds and actual generations are recorded
([GENETIC_BUDGET.md](GENETIC_BUDGET.md)).

## 3. Quality gate (3.3.2)

One assessment per model on log C (`--diagnostics` only for bounded nets; the
unbounded Alpha, Heuristics and Genetic nets get soundness, token and simplicity values):

```powershell
py scripts/assess_model.py results/models/inductive_miner.pnml --name inductive_miner --out results/assessment --diagnostics
py scripts/assess_model.py results/models/heuristics_miner.pnml --name heuristics_miner --out results/assessment
py scripts/assess_model.py results/alpha/alpha_miner.pnml --name alpha_miner --out results/assessment
py scripts/assess_model.py results/genetic/seed_20261025/models/genetic_miner.pnml --name genetic_miner --out results/assessment
foreach ($t in "0.5", "0.7", "0.9", "0.99") {
    py scripts/assess_model.py results/heuristics/dep_$t/model.pnml --name heuristics_dep_$t --out results/assessment
}
py scripts/discover_alpha.py --audit
py scripts/audit_dead_transitions.py
py scripts/audit_genetic_dead_transitions.py
```

Background per miner: [ALPHA_MINER.md](ALPHA_MINER.md), [HEURISTICS_SWEEP.md](HEURISTICS_SWEEP.md),
[EVALUATION.md](EVALUATION.md); all records: [results/assessment/README.md](../results/assessment/README.md).
The optional optimal HM alignments (`evaluate_models.py`) are expensive; finished
variants are checkpointed and reused.

## 4. Refinement before the event abstraction (3.3.3, archived)

Reproduces the earlier final model kept in `results/before_abstraction/`
([REFINEMENT.md](REFINEMENT.md), [MANUAL_EDITS.md](MANUAL_EDITS.md)):

```powershell
py scripts/refine_model.py
py -m scripts.refine_frequent
py -m scripts.export_refined_model
py scripts/assess_model.py results/refinement/final_model.pnml --name refined_imf --out results/assessment --diagnostics
py scripts/manual_edits.py
py scripts/render_manual_edits.py
py scripts/export_final_model.py --source results/manual_edits/selected/model.ptml --cache tmp/evaluation/projected_sequences.json --out results/before_abstraction/final
```

## 5. Event abstraction and final model (3.3.3)

[EVENT_ABSTRACTION.md](EVENT_ABSTRACTION.md):

```powershell
py scripts/abstract_log.py
py scripts/refine_abstracted.py
py scripts/assess_model.py results/abstraction/base/model.pnml --name abstracted_base --out results/assessment --diagnostics --cache tmp/evaluation/abstracted_sequences.json
py scripts/manual_edits_abstracted.py
py scripts/export_final_model.py
py scripts/assess_model.py results/final/final_model.pnml --name final_model --out results/assessment --diagnostics --cache tmp/evaluation/abstracted_sequences.json
```

## 6. Decision mining (3.3.4)

Uses `results/final/` and the sequence cache named in its manifest; the same
abstraction is applied to the raw events, so event attributes stay attached
([DECISION_MINING.md](DECISION_MINING.md)). The case-wise 70/30 split uses seed 20261018.

```powershell
py scripts/mine_decisions.py
py scripts/render_decision_stages.py
py scripts/render_branch_probabilities.py
py scripts/render_decisions.py
py scripts/verify_decisions.py
py scripts/export_signavio.py
```

## 7. Comparisons and tables

Need the case split written by decision mining:

```powershell
py scripts/holdout_check.py
py scripts/compare_abstraction.py
py scripts/render_abstraction.py
py scripts/render_model_comparison.py
py scripts/render_metric_methods.py
py scripts/render_assessment_index.py
```

## 8. Report

Copy audited tables and figures into `report/` (hashes go to `docs/manifests/`),
then build the PDF. The build needs a TeX distribution with Latexmk and Perl,
but no Python and no data.

```powershell
py scripts/select_feedback_report.py
py scripts/select_decision_report.py
py scripts/select_miner_overview.py
py scripts/select_genetic_report.py
py scripts/verify_decisions.py --artifacts-only
.\report\build.ps1
```

Output: `report/build/main.pdf` (ignored by Git). Details: [report/README.md](../report/README.md).

## 9. Tests

```powershell
py -m pip check
py -m unittest discover -s tests -v
```

53 tests on small examples cover the projection, the event abstraction, metric
calculations, case weighting, resumable alignments, model semantics and
decision-input timing. A full `verify_decisions.py` run needs the ignored
observation files, so run `mine_decisions.py` first.

## Inspect results interactively

```powershell
.\scripts\start_jupyter.ps1                 # notebooks/01_getting_started.ipynb, kernel "BPIC17 (.venv)"
py scripts/setup_bpmn_viewer.py             # once
py -m http.server 8787 --bind 127.0.0.1     # keep running
```

- <http://127.0.0.1:8787/results/decision_mining/viewer.html>: final BPMN with the rule at every XOR
- <http://127.0.0.1:8787/results/decision_mining/index.html>: decision trees and evaluation

After moving the project folder, register the notebook kernel again:
`py -m ipykernel install --prefix .venv --name bpic17 --display-name "BPIC17 (.venv)"`.
