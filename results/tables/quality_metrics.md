# BPIC-17: Qualitätsvergleich

31.509 Fälle, 475.306 abgeschlossene Events; dieselbe Projektion für beide Modelle.

| Metrik | Inductive Miner | Heuristics Miner | Richtung |
|---|---:|---:|---|
| Token replay fitness | 1.0000 | 0.8334 | größer |
| Token mean trace fitness | 1.0000 | 0.8240 | größer |
| Token fitting cases (%) | 100.00 | 0.00 | größer |
| Alignment fitness | 0.9998 | incomplete | größer |
| Alignment mean trace fitness | 1.0000 | incomplete | größer |
| Alignment fitting cases (%) | 100.00 | incomplete | größer |
| Replay upper bound (%) | 100.00 | 1.30 | größer |
| Token precision | 0.2926 | 0.9978 | größer |
| Alignment precision | 0.2926 | 0.9975 | größer |
| Unfit Align-ET prefixes (%) | 0.00 | 84.35 | kleiner |
| Token generalization | 0.9757 | 0.8611 | größer |
| Arc-degree simplicity | 0.6170 | 0.4815 | größer |
| Nodes (own) | 87 | 143 | kleiner |
| Arcs (own) | 114 | 220 | kleiner |
| Extended Cardoso (own) | 47 | 108 | kleiner |
| Extended Cyclomatic (own) | 1552 | unbounded | kleiner |
| PM4Py Cyclomatic* | 2397 | not_applicable | kleiner |

*PM4Py Cyclomatic: dokumentierter Implementierungsfehler in Version 2.7.23.11; siehe docs/EVALUATION.md.

Token Replay ist heuristisch. HM ist unbeschränkt; ein hoher Token-Precisionwert allein belegt keine Modellqualität.

[Definitionen, Quellen und Einschränkungen](../../docs/EVALUATION.md).

HM: Mindestens 31,098 Fälle sind wegen unerreichbarer Aktivitäten nicht vollständig replaybar; höchstens 411 von 31,509 Fällen könnten passen. Das ist eine bewiesene Obergrenze, kein gemessener Alignment-Anteil.

Zusätzliche HM-Alignment-Fitness: incomplete; letzter gespeicherter begrenzter Lauf mit 21501 vollständig berechneten Fällen. Kein Gesamtmittelwert einer Teilmenge.
