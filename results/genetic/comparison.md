# Third discovery experiment: native PM4Py Genetic Miner

Genetic seed: 20261025; population: 10; actual generations: 2/6; native objective: 0.304897.

| Model | Train cases | Token fitness | Token fitting % | Token precision | Generalization | Arc simplicity | Nodes | Cardoso | Exact coverage % | Sound | State space |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| IM | 31509 | 1.0000 | 100.00 | 0.2926 | 0.9757 | 0.6170 | 87 | 47 | 100.0000 | True | ok |
| HM | 31509 | 0.8334 | 0.00 | 0.9978 | 0.8611 | 0.4815 | 143 | 108 | not enumerated | False | unbounded |
| Genetic | 31509 | 0.7410 | 0.00 | 0.5970 | 0.9828 | 0.7755 | 76 | 43 | not enumerated | False | unbounded |
| Refined IMf | 18918 | 0.9875 | 81.62 | 0.5952 | 0.9912 | 0.7008 | 89 | 52 | 80.4532 | True | ok |

Same full completion evaluation log, 31,509 cases; refined training set differs and is explicit.
Token-based scores do not establish soundness or exact case replay; see the explicit sound field.
A single small seeded Genetic run is exploratory; no globally best model is claimed.
Genetic net is provably unbounded (PM4Py witness crosscheck). Exact whole-case coverage is not enumerated; 0% token fitting is heuristic.
The original duplicate-ID export was corrected from its intact source graph; native objective reproduced exactly. Invalid initial scores are excluded.

HM exact-replay upper bound: 1.3044%; this is not an observed fitting percentage.
The refined IMf row describes its original unguarded structure; hard-guard test coverage remains 10.19%.

[Parameters and reasons](../../docs/MINER_PARAMETERS.md) | [Design choices](../../docs/DESIGN_DECISIONS.md)
