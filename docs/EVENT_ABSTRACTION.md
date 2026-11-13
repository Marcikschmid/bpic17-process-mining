# Event abstraction before refinement

Keyword notes for the author's own report text (question: "is the model bloated;
are there raw events that are not edge cases but unnecessary, making the model
complex and less generalizable?"). Numbers from `results/abstraction/` and
`results/assessment/`; regenerate with the commands at the end.

## Diagnosis: the earlier final model was bloated by logging artefacts

Earlier final model (`results/before_abstraction/final/`, IMf + G2+G3+R3+R4):
98 nodes, 25 tasks, 18 XOR pairs, 2 AND pairs. Elements without own process meaning:

| Element | Count | Cause |
|---|---:|---|
| Tasks `W_Handle leads`, `W_Complete application`, `W_Validate application`, `W_Call incomplete files` | 4 of 25 | work-item completion events (mirror of an `A_` state change) |
| Tasks `O_Created`, `O_Accepted` | 2 of 25 | same system action as `O_Create Offer` / `A_Pending` |
| XOR splits D05, D08, D11, D12, D17 | 5 of 18 | decide only whether a work-item `complete` was logged |
| Loop splits D01, D09, D10, D16, D18 | 5 of 18 | repeat simultaneous per-offer events (`O_Cancelled`, `O_Refused`, `O_Sent`) |
| AND block around `W_Validate application` | 1 of 2 | work item parallel to the whole validation phase |

- Decision trees at D05 / D08: balanced accuracy 0.600 / 0.528 (close to chance) -> no business decision behind them.
- Not noise in the frequency sense: `W_Complete application` in 60.6 % of cases, `W_Validate application` in 34.6 %.

## Why abstraction and not another filter (alternatives checked)

| Measure | Result | Verdict |
|---|---|---|
| Stronger frequency filtering on the unchanged log (IMf noise / fewer training variants, 45 settings) | no candidate >= 80 % replay is smaller AND more precise; smaller ones (71-83 nodes) have Align-ET 0.24-0.53 | artefacts are frequent -> not removed; real rare paths removed instead |
| Delete the W_ tasks only in the model | at most 21.09 % exact replay (cases without any of the 5 W_ labels) | log still contains the events |
| Event abstraction in preprocessing | see results below | removes the cause; all cases kept |

## Rules (`src/event_abstraction.py`) and evidence (`results/abstraction/abstraction_audit.json`)

- Applied per case on the completion projection, original XES order, raw timestamps.
- MIRROR (drop): `O_Created` (always directly after `O_Create Offer`, 100 % <= 60 s, median 1.0 s); `O_Accepted` (always directly before `A_Pending`, 99.98 % <= 1 s).
- WORK_ITEM (drop): completion events of `W_Complete application`, `W_Validate application`, `W_Call incomplete files`, `W_Handle leads`, `W_Call after offers`.
  - `complete` share of their raw events: 12.8 / 7.6 / 1.7 / 7.4 / 0.2 % (rest: schedule, start, suspend, resume, abort, withdraw).
  - completion next to an `A_` event within 1 s: 99.7 / 89.2 / 79.5 / 99.9 / 54.1 %.
  - partner events: `A_Complete`, `A_Incomplete`/`A_Pending`, `A_Validating`, `A_Concept`, `A_Validating`.
- SIMULTANEOUS (collapse direct repetition within 1 s): `O_Cancelled` (4,429 repetitions, 99.5 % <= 1 s), `O_Refused` (975, 100 %), `O_Sent (mail and online)` (3,111, 99.9 %), `O_Sent (online only)` (85, 100 %). Repetitions > 1 s apart are kept.
- KEPT as edge cases: `W_Assess potential fraud` (282 events, 0.85 % of cases; fraud check), `O_Sent (online only)` (5.7 % of cases; second send channel), late cancellation, denied applications.
- Applied: 60,223 mirror events and 41,580 work-item completions dropped, 8,573 simultaneous repetitions collapsed.
- Effect: events 475,306 -> 364,930; labels 24 -> 17; variants 5,623 -> 2,680; cases in singleton variants 13.17 % -> 5.99 %; variants needed for 80 % of cases 610 -> 67; all 31,509 cases kept.
- Decision attributes unaffected: all event attributes used in decision mining are on `O_Create Offer` (kept).

## Discovery on the abstracted log (`scripts/refine_abstracted.py`)

- Same family as before: most frequent variants up to a coverage (0.50-0.95) plus all cases (1.00), IMf noise 0/0.03/0.05/0.10/0.20; 55 settings, 53 evaluated (2 exceed the 50,000-state cap), all on all cases.
- Rule: sound, exact replay >= 80 %, max Align-ET, tie fewer nodes.
- Deviation stated openly: upper band bound 82 % (own choice) dropped; no candidate in [80, 82] (gap 77.61 -> 85.35 %); the bound would exclude candidates better in replay, precision and size than every band candidate of the unabstracted log.
- Selected base `abstracted_0.70_imf_0.00` (same tree for 5 settings): 85.35 % exact replay, Align-ET 0.766, 46 nodes.

## Manual edits on the abstracted base (`src/tree_edits_abstracted.py`)

- Diagnostics of the base (`results/assessment/abstracted_base_diagnostics/`): escaping `O_Create Offer`/`A_Accepted` -> `A_Complete` (35,007 / 31,484), `A_Complete` -> `A_Pending`/`O_Returned` (30,349), `A_Validating` -> `A_Validating` (29,090); log moves `O_Create Offer` (2,263 cases), `O_Sent (online only)` (2,026), `O_Cancelled` (1,754).
- Five edits, each one tree block; all 32 combinations screened; same guards as before (generalization drop <= 0.01, arc-degree drop <= 0.05, nodes <= +25 %).

| Edit | Evidence | Exact % | Align-ET | Nodes |
|---|---|---:|---:|---:|
| base | - | 85.35 | 0.766 | 46 |
| R1 `A_Complete` after first sent offer | 0 of 31,362 cases against | 85.35 | 0.826 | 56 |
| R2 validation round starts with `A_Validating` | 0 / 0 before first validation; reverse order in 1,157 cases | 83.33 | 0.762 | 46 |
| R3 pending/denial only after validation | 0 / 169 cases against | 85.03 | 0.789 | 49 |
| G1 online-only send channel | 1,800 cases | 87.28 | 0.772 | 49 |
| G2 new offer between validation rounds | 1,807 cases | 85.70 | 0.769 | 54 |

- Guard stage: 9 more precise candidates fail the node guard (all contain R1 plus at least one further edit; e.g. R1+R3: Align-ET 0.857, 59 nodes = +28 %); first passing candidate: R1 -> selected. The node guard (+25 %) was kept unchanged although the base is now much smaller (46 vs. 89 nodes).
- R1 here passes the generalization guard (0.989 vs. 0.992), unlike before abstraction (0.972 vs. 0.991): the duplicated offer block is smaller.

## Result

| | Final before abstraction | Final (abstraction + R1) |
|---|---:|---:|
| Evaluation log | completion projection | abstracted log |
| Exact whole-case replay | 80.43 % | 85.35 % |
| Alignment fitness | 0.979 | 0.983 |
| Align-ET precision | 0.695 | 0.826 |
| Alignment generalization | 0.988 | 0.989 |
| Arc-degree simplicity | 0.710 | 0.700 |
| Nodes / Ext. Cardoso / ECyM | 98 / 55 / 166 | 56 / 30 / 35 |
| BPMN tasks / XOR pairs / AND pairs | 25 / 18 / 2 | 17 / 11 / 2 |

### Fair comparison on ONE log (`results/abstraction/comparison.csv`)

Earlier models projected onto the abstracted log (dropped labels hidden as silent transitions):

| Model | Exact % | Align-ET | Nodes | Visible tasks |
|---|---:|---:|---:|---:|
| IM (baseline) | 100.00 | 0.294 | 87 | 17 |
| Refined IMf before abstraction | 82.94 | 0.683 | 89 | 15 |
| Final before abstraction (G2+G3+R3+R4) | 82.13 | 0.788 | 98 | 19 |
| Abstracted IMf (before edits) | 85.35 | 0.766 | 46 | 15 |
| **Final (abstraction + R1)** | **85.35** | **0.826** | **56** | 17 |

- Same log: final model better in replay (+3.22 pp), precision (+0.038) and size (-42 nodes) than the earlier final model.
- Alignment generalization not compared here: hidden transitions never used by alignments count as unused (bias against projected models).

### Generalization (`results/comparison/holdout_check.json`, case split seed 20261018)

- Train-only rediscovery gives the identical tree in both pipelines.
- Test cases whose variant never occurs in training: 14.70 % -> 6.76 %.
- Final model train/test exact replay: before 80.48 / 80.32 %, after 85.33 / 85.39 %.
- Replay by outcome before -> after: Pending 79.00 -> 83.28 %, Denied 75.24 -> 84.99 %, Cancelled 85.42 -> 89.68 %, no terminal state (98 cases, still running at log end) 0 -> 0 %.

### Decision mining on the new final model (`results/decision_mining/`)

- 11 XOR splits (7 choices, 4 loops, all two-way) instead of 18; 304,527 aligned decisions instead of 425,851.
- Feature stages (fixed CART): case 0.535 -> + event 0.632 -> + engineered 0.701; tuned final 0.790; 11 / 11 above chance.
- Not directly comparable with the earlier 0.810: the removed artefact splits (e.g. old D10/D11/D01, 0.97-0.98) were easy counting/logging decisions.
- Hard guards: 4,130 / 31,509 = 13.11 % (test 13.28 %) instead of 7.18 % (7.09 %): fewer decisions per case must all be right.
- BPMN with rule blocks: 9 report panels (decision blocks D01-D11), Signavio files regenerated and checked.

## Limitations

- Different event set -> values on the completion projection and on the abstracted log are not directly comparable; use the common-log table.
- Work-item perspective (who worked how long, aborted work) is not in the control-flow model; it was already outside the completion projection, the abstraction only removes its residue.
- Collapsing simultaneous repetitions loses the number of offers affected by one cancellation/refusal; the number of offers stays visible through `O_Create Offer`.
- The rule change (no upper band bound) was made after the exploratory abstraction run; stated as deviation.
- Edits screened on all cases (incl. decision-mining test cases); hold-out is a stability check.

## Reproduction

```powershell
.\.venv\Scripts\python.exe scripts/abstract_log.py
.\.venv\Scripts\python.exe scripts/refine_abstracted.py
.\.venv\Scripts\python.exe scripts/assess_model.py results/abstraction/base/model.pnml --name abstracted_base --out results/assessment --diagnostics --cache tmp/evaluation/abstracted_sequences.json
.\.venv\Scripts\python.exe scripts/manual_edits_abstracted.py
.\.venv\Scripts\python.exe scripts/export_final_model.py
.\.venv\Scripts\python.exe scripts/assess_model.py results/final/final_model.pnml --name final_model --out results/assessment --diagnostics --cache tmp/evaluation/abstracted_sequences.json
.\.venv\Scripts\python.exe scripts/mine_decisions.py
.\.venv\Scripts\python.exe scripts/render_decision_stages.py
.\.venv\Scripts\python.exe scripts/render_branch_probabilities.py
.\.venv\Scripts\python.exe scripts/render_decisions.py
.\.venv\Scripts\python.exe scripts/verify_decisions.py
.\.venv\Scripts\python.exe scripts/export_signavio.py
.\.venv\Scripts\python.exe scripts/holdout_check.py
.\.venv\Scripts\python.exe scripts/compare_abstraction.py
.\.venv\Scripts\python.exe scripts/render_abstraction.py
.\.venv\Scripts\python.exe scripts/render_model_comparison.py
.\.venv\Scripts\python.exe scripts/render_assessment_index.py
.\.venv\Scripts\python.exe scripts/select_feedback_report.py
.\.venv\Scripts\python.exe scripts/select_decision_report.py
```

The earlier final model and its decision mining/Signavio outputs are archived unchanged in
`results/before_abstraction/` (their per-decision training rows were moved to the ignored
`tmp/before_abstraction/`).
