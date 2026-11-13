# Final model before the event abstraction (archived 2026-11-12)

Frozen outputs of the earlier final model (refined IMf + manual edits G2+G3+R3+R4,
evaluated on the full completion projection `tmp/evaluation/projected_sequences.json`).
Kept for the before/after comparison of the event abstraction
([`docs/EVENT_ABSTRACTION.md`](../../docs/EVENT_ABSTRACTION.md), design decision D37).

| Folder / file | Content |
|---|---|
| `final/` | PTML, PNML, BPMN, block structure and figures (80.43 % exact replay, 98 nodes, 25 tasks, 18 XOR / 2 AND pairs) |
| `assessment/` | Full quality and soundness record with conformance diagnostics (Align-ET 0.695) |
| `decision_mining/` | Decision mining on this model (18 splits, balanced accuracy 0.810, hard guards 7.09 % on test cases); per-decision training rows moved to the ignored `tmp/before_abstraction/` |
| `signavio/` | SAP Signavio import files of this model |
| `holdout_check.{json,tex}` | Hold-out check as it was before the abstraction |

The manual-edit screen of this model stays in `results/manual_edits/` ([`docs/MANUAL_EDITS.md`](../../docs/MANUAL_EDITS.md)).
The current final model is in `results/final/`.
