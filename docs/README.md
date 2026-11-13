# Documentation

Method notes are keyword-style records with the numbers behind each result;
they are written as material for the author's report, not as finished text.
Language: EN = English, DE = German.

## Start here

| Document | Content | Lang |
|---|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Pipeline, code layers, data artefacts, module map, design invariants | EN |
| [REPRODUCE.md](REPRODUCE.md) | Every command in pipeline order, tests, report build | EN |
| [CONCEPTS.md](CONCEPTS.md) | Event, case, trace, variant: definitions and BPIC-17 values | EN |
| [DESIGN_DECISIONS.md](DESIGN_DECISIONS.md) | 37 design decisions with alternatives, evidence and limitations | DE |

## By assignment step

| Step | Document | Content | Lang |
|---|---|---|---|
| 3.2 | [STATISTICS.md](STATISTICS.md) | Raw-log statistics and their independent verification | DE |
| 3.3.1 | [DISCOVERY.md](DISCOVERY.md) | Common input, IM/HM baselines, Genetic run | DE |
| 3.3.1 | [ALPHA_MINER.md](ALPHA_MINER.md) | Alpha Miner baseline | EN |
| 3.3.1 | [HEURISTICS_SWEEP.md](HEURISTICS_SWEEP.md) | Native heuristics net and dependency sweep | EN |
| 3.3.1 | [GENETIC_BUDGET.md](GENETIC_BUDGET.md) | Genetic Miner budget and early stop | EN |
| 3.3.1 | [MINER_PARAMETERS.md](MINER_PARAMETERS.md) | Every miner parameter: default, value, reason | DE |
| 3.3.2 | [EVALUATION.md](EVALUATION.md) | Quality dimensions and how they are measured | DE |
| 3.3.3 | [EVENT_ABSTRACTION.md](EVENT_ABSTRACTION.md) | **Final model:** logging artefacts vs. edge cases, rediscovery, edits, before/after | EN |
| 3.3.3 | [REFINEMENT.md](REFINEMENT.md) | IMf refinement before the abstraction (archived path) | DE |
| 3.3.3 | [MANUAL_EDITS.md](MANUAL_EDITS.md) | Manual edits before the abstraction (archived path) | EN |
| 3.3.4 | [DECISION_MINING.md](DECISION_MINING.md) | Branch probabilities, CART rules, guard coverage | DE |
| 3.3.4 | [SIGNAVIO.md](SIGNAVIO.md) | Importing the final model into SAP Signavio | DE |

## Cross-cutting

| Document | Content | Lang |
|---|---|---|
| [OPTIMIZATION.md](OPTIMIZATION.md) | What was optimized, by which criterion, how | DE |
| [CHECKLIST.md](CHECKLIST.md) | Assignment checklist and open items | DE |
| [AI_USAGE.md](AI_USAGE.md) | Record of AI-assisted work (basis for the required declaration) | DE |
| [manifests/](manifests/) | Machine-readable provenance: report copies, tool installs, Genetic verification | JSON |

Further READMEs: [scripts/](../scripts/README.md), [results/](../results/README.md),
[assessment records](../results/assessment/README.md), [report/](../report/README.md),
[data/](../data/README.md), [literature/](../literature/README.md).
