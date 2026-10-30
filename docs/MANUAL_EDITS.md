# Manual edits of the refined IMf model

Keyword notes for the author's own report text (tutor: "can single flows of the
Petri net be changed manually to optimise the metric further; justify which flow
was changed and why"). Numbers from `results/manual_edits/` and
`results/assessment/`; regenerate with the commands at the end.

## Starting point and goal

- Base: refined IMf model `frequent_0.60_imf_0.03` (40-candidate refinement, `docs/REFINEMENT.md`): sound, 80.45 % exact whole-case replay, Align-ET precision 0.598, 89 nodes.
- Goal (simulation base model): keep soundness and at least 80 % exact replay (band 80-82 %: lower bound = lecture slide 36 "at least 80% of all cases", upper bound own choice, unchanged from refinement); raise precision = remove behaviour the log never shows, because a simulation would generate such unobserved paths.
- Guard rails for the other two criteria (fixed before screening): alignment generalization drop <= 0.01, arc-degree simplicity drop <= 0.05, node increase <= 25 %.

## Why edits on the process tree, not on single Petri-net arcs

- Editing arcs directly can break soundness (deadlocks, unbounded places) and block structure; PM4Py's net-to-BPMN conversion is node-wise and does not restore block structure.
- Each edit replaces one block of the process tree (`src/tree_edits.py`); the Petri net is derived with `pm4py.convert_to_petri_net` -> sound and block-structured by construction, and the BPMN stays a clean SESE-block model.
- Every edit is still documented as a Petri-net delta (places, transitions, silent transitions, arcs, added/removed visible transitions) in `results/manual_edits/screen.json` (`petri_net_delta`).

## Where to edit: conformance checking after mining

- Pre-edit diagnostics (`results/assessment/refined_imf_diagnostics/`): Align-ET escaping edges = precision leaks; log moves of optimal alignments = fitness leaks.
- Largest precision leaks: `O_Create Offer`/`O_Created`/`A_Accepted` -> `A_Complete` (35,006 / 35,006 / 31,483 weighted prefixes), `O_Sent` -> `O_Sent` (33,899), `A_Validating` -> `A_Validating` and -> `W_Call incomplete files` (33,294 each), `A_Complete` -> `O_Returned` / `A_Incomplete` (30,349 each).
- Largest fitness leaks (log moves, cases): `O_Sent (online only)` 2,026 (not in the model at all), `O_Cancelled` 1,964, `O_Returned` 1,904, `O_Refused` 991.
- Mapping diagnostic -> edit: `results/manual_edits/conformance_to_edits.tex`.

## The seven edits and their log evidence (all 31,509 cases)

| Edit | Type | Block changed | Log evidence | Exact replay | Align-ET | Nodes |
|---|---|---|---|---:|---:|---:|
| base | - | - | - | 80.45 % | 0.598 | 89 |
| R1 | restricting | `A_Complete` no longer parallel to the whole offer loop; only after the first offer was sent | `A_Complete` after first `O_Sent` in 31,362 of 31,362 cases; before: 0 | 80.42 % | 0.656 | 111 |
| R2 | restricting | no direct repetition of `O_Sent (mail and online)` | direct repetition in 2,781 cases (8.83 %) | 74.17 % | 0.624 | 84 |
| R3 | restricting | validation phase as observed order: `A_Validating` -> `O_Returned` -> incomplete-files loop -> outcome | `O_Returned` / `A_Incomplete` before first `A_Validating`: 0 / 0 cases | 77.90 % | 0.697 | 84 |
| R4 | restricting | `O_Cancelled` only after `A_Cancelled` (mandatory) or `A_Pending` (optional) | `O_Cancelled` after `A_Denied` in 195 cases only | 80.45 % | 0.598 | 92 |
| G1 | generalizing | second send channel `O_Sent (online only)` | in 1,800 cases (5.71 %) | 81.88 % | 0.585 | 90 |
| G2 | generalizing | late cancellation `A_Cancelled` as third validation outcome | after `A_Validating` in 1,014 cases (3.22 %) | 81.52 % | 0.595 | 90 |
| G3 | generalizing | several refused offers (`O_Refused` loop) | >= 2 `O_Refused` in 777 cases (2.47 %) | 82.06 % | 0.597 | 92 |

- Restricting edits (R*) shrink the model language -> exact replay can only stay or fall; budget to the 80 % floor (25,208 cases): 142 cases (0.45 pp).
- Generalizing edits (G*) add observed behaviour -> buy back replay for restricting edits; cost: small precision loss.
- R2 alone already leaves the band (-6.28 pp): direct `O_Sent` repetitions are real (8.83 % of cases) -> no combination with R2 is in the band.
- R3 = largest single precision gain (+0.100) and smaller model (84 nodes), but alone below the band (77.90 %) -> needs a generalizing partner.
- R1 = strongest log evidence (0 counterexamples) and +0.058 precision, but duplicates the offer block (5 duplicated visible labels, 111 nodes).

## Screening of all 2^7 = 128 combinations

- Every combination: exact replay (all cases), Align-ET (exact finite-state solver, PM4Py-identical), soundness via complete state space, size, Extended Cardoso, ECyM, arc degree (`results/manual_edits/screen.csv`).
- All 128 combinations sound (process trees).
- 28 combinations inside the band 80-82 % (40 inside 78-82 %).

## Selection rule (fixed before any combination was evaluated)

1. sound and 80 % <= exact replay <= 82 %;
2. maximise Align-ET precision;
3. guard rails on the full assessment (alignment generalization, arc degree, nodes vs. base);
4. tie: fewer nodes.

Run history (deviations stated openly):

- Run 1: guard stage on the top 5, token-based generalization -> invalid for edits that duplicate labels (PM4Py token replay maps each label to one transition; token precision 0.997 implausible) -> switched to alignment-based generalization (PM4Py formula on exact optimal alignments) before any selection.
- Run 2: guard stage on the top 10 -> all 10 contain R1 and all fail the generalization guard (0.972 vs. base 0.991, drop 0.019 > 0.01) -> no selection.
- Run 3 (2026-10-30): same rule, guard stage walks down the ranking until the first candidate passes (no cap); already computed full assessments reused -> G3+R3+R4 (79.39 %).
- Run 4 (2026-10-30, after lecture of 2026-10-29, slide 36 "at least 80% of all cases"): lower band bound 78 -> 80 %; refinement base unchanged under [80, 82] (all other refinement candidates are < 80 % or > 82 %); same edits, same guards.
- Why R1 fails: duplicated offer transitions split the execution counts; the generalization formula `1 - mean(1/sqrt(n_t))` penalises rarely executed transitions -> R1 trades precision against generalization, exactly the trade-off the guard rail is for.

## Result: G2 + G3 + R3 + R4

- Guard stage (band 80-82 %): 8 candidates with R1 rejected (alignment generalization 0.9717-0.9724, drop > 0.01; 5 of them also > 25 % more nodes); first candidate without R1 = G2+G3+R3+R4 -> passes all guards -> selected (`results/manual_edits/guard_stage.tex`).
- Earlier selection under the 78 % floor (run 3): G3+R3+R4 (79.39 %, Align-ET 0.697) -> below "at least 80 %" -> replaced.

| | Base (IMf) | Final (G2+G3+R3+R4) | Change |
|---|---:|---:|---:|
| Exact whole-case replay | 80.45 % (25,350) | 80.43 % (25,343) | -0.02 pp (-7 cases) |
| Alignment fitness | 0.9765 | 0.9786 | +0.0021 |
| Align-ET precision | 0.598 | 0.695 | +0.097 |
| Alignment generalization | 0.9911 | 0.9880 | -0.0031 |
| Arc-degree simplicity | 0.701 | 0.710 | +0.009 |
| Nodes | 89 | 98 | +9 |
| Extended Cardoso / ECyM | 52 / 551 | 55 / 166 | +3 / -385 |
| Reachable markings | 187 | 94 | -93 |

- Petri-net delta vs. base: +2 places, +7 transitions (3 silent), +10 arcs; visible transitions added: second `A_Validating` (incomplete-files loop), second `A_Cancelled` (late cancellation), two more `O_Cancelled` (cancelled branches, pending branch).
- Why these four, in words of the evidence: R3 = validation order never violated in the log (0 counterexamples) and removes the AND-block around `O_Returned`/`A_Incomplete` -> largest precision gain; R4 = `O_Cancelled` only where the log shows it (195 denied cases with `O_Cancelled` sacrificed); G3 = 777 cases with repeated `O_Refused` regained; G2 = 1,014 cases cancelled after validation regained -> together they bring R3 back above 80 %.
- Not chosen: R1 (precision +0.058 but fails generalization guard, see above); R2 (8.83 % of cases repeat `O_Sent` -> leaves band); G1 (lower precision than G2 at similar replay gain).
- BPMN: 25 tasks (21 labels; `A_Cancelled`, `A_Validating`, `O_Cancelled` duplicated), 18 XOR split/merge pairs (9 choices + 9 loops), 2 AND pairs; language-equivalent to the Petri net (`results/final/manifest.json`).
- Held-out: final model replays 80.48 % of training and 80.32 % of test cases (`results/comparison/holdout_check.json`).
- Caveat: edits screened on all cases (incl. the decision-mining test cases); the control-flow discovery itself is unchanged by a train-only rerun.

## Reproduction

```powershell
.\.venv\Scripts\python.exe scripts/manual_edits.py
.\.venv\Scripts\python.exe scripts/render_manual_edits.py
.\.venv\Scripts\python.exe scripts/export_final_model.py
.\.venv\Scripts\python.exe scripts/assess_model.py results/final/final_model.pnml --name final_model --out results/assessment --diagnostics
```
