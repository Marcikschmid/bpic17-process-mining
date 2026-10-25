# Refinement summary (Assignment 3.3.3)

Selected: `frequent_0.60_imf_0.03`

Exact replay: **25,350/31,509 cases (80.4532%)**.
Discovery training: 18,918 cases; evaluation: all 31,509 cases.

| Metric | IM baseline | Refined |
|---|---:|---:|
| Exact complete-case replay (%) | 100 | 80.4532 |
| Token replay fitness | 1.0000 | 0.9875 |
| Token fitting cases (%) | 100.0000 | 81.6243 |
| Token precision | 0.2926 | 0.5952 |
| Align-ET precision | 0.2926 | 0.5977 |
| Token generalization | 0.9757 | 0.9912 |
| Arc-degree simplicity | 0.6170 | 0.7008 |
| Nodes | 87 | 89 |
| Arcs | 114 | 108 |
| Extended Cardoso | 47 | 52 |
| Extended Cyclomatic | 1,552 | 551 |

Align-ET excludes 40,338 weighted nonempty prefixes; denominator 443,797.
Token replay is heuristic; its fitting-case fraction and fitness are separate from exact language acceptance. PM4Py defaults may ignore activities missing from the model.
Generalization is the PM4Py frequency heuristic on the full evaluation log, not held-out predictive validation.

## Published BPIC-17 results

| Source | Reported result | Comparability |
|---|---|---|
| [Rodrigues et al., academic winner](https://ais.win.tue.nl/bpi/2017/bpi2017_winner_academic.pdf), PDF pp. 3, 7-9 | Fitness 97.28%; precision 98.72%; 19 model versions | 100 cases removed; activity abstraction; different log/model representation; no exact whole-case coverage comparison |
| [Povalyaeva et al., student winner](https://ais.win.tue.nl/bpi/2017/bpi2017_winner_student.pdf), PDF p. 3 | BPMN 2.0 using Celonis; raw 31,509 cases and 1,202,267 events | Structural/domain comparison; no matched four-dimension quality score used |
| [Blevi et al., KPMG](https://ais.win.tue.nl/bpi/2017/bpi2017_winner_professional.pdf), PDF pp. 2-3 | Approximately 22 days and 27% multiple-offer cases | Our raw mean 21.900 days; multiple-offer cases 27.164%; contextual check, not conformance |

## Excluded activity labels

`O_Sent (online only)`, `W_Assess potential fraud`, `W_Call after offers`

All cases containing these labels remain in evaluation; no fitting subset is substituted. Rare paths and residual concurrency remain limitations. Additional duration/resource distributions and decision probabilities are required for a calibrated simulation.
