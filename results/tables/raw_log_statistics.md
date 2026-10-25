# Raw event log statistics (Assignment 3.2)

Source SHA256: `183c5e5189282779c811c78c33ff936351b3dd201165d612211fc220936f8249`

| Statistic | Value |
|---|---:|
| Cases | 31,509 |
| Events | 1,202,267 |
| Variants (activity sequence) | 15,930 |
| Distinct case attribute names | 4 |
| Distinct event attribute names | 15 |
| Case length: mean (events) | 38.156 |
| Case length: population SD | 16.715 |
| Duration: mean (days) | 21.900 |
| Duration: mean (minutes) | 31,535.432 |
| Duration: mean (seconds) | 1,892,125.923 |
| Duration: population SD (days) | 13.169 |
| Duration: population SD (minutes) | 18,963.394 |
| Duration: population SD (seconds) | 1,137,803.635 |
| Categorical event attributes (incl. IDs) | 9 |
| Categorical event attributes (excl. IDs) | 7 |
| Distinct activity names | 26 |
| Distinct resource values (incl. system) | 149 |
| Variants occurring once | 13,907 |
| Top 10 variants: cases (%) | 15.33 |

Duration: max timestamp minus min timestamp in UTC; original event order retained for variants.
Population SD (ddof=0); sample SD and quantiles are also in the JSON export.

| Scope | Attribute | Classification | Distinct | Missing (%) |
|---|---|---|---:|---:|
| case | `ApplicationType` | categorical | 2 | 0.00 |
| case | `LoanGoal` | categorical | 14 | 0.00 |
| case | `RequestedAmount` | numeric | 701 | 0.00 |
| case | `concept:name` | nominal ID | 31,509 | 0.00 |
| event | `Accepted` | categorical | 2 | 96.42 |
| event | `Action` | categorical | 5 | 0.00 |
| event | `CreditScore` | numeric | 520 | 96.42 |
| event | `EventID` | nominal ID | 1,202,267 | 0.00 |
| event | `EventOrigin` | categorical | 3 | 0.00 |
| event | `FirstWithdrawalAmount` | numeric | 5,930 | 96.42 |
| event | `MonthlyCost` | numeric | 5,816 | 96.42 |
| event | `NumberOfTerms` | numeric | 147 | 96.42 |
| event | `OfferID` | nominal ID | 42,995 | 87.45 |
| event | `OfferedAmount` | numeric | 663 | 96.42 |
| event | `Selected` | categorical | 2 | 96.42 |
| event | `concept:name` | categorical | 26 | 0.00 |
| event | `lifecycle:transition` | categorical | 7 | 0.00 |
| event | `org:resource` | categorical | 149 | 0.00 |
| event | `time:timestamp` | timestamp | 1,202,209 | 0.00 |

Timestamp order: 0 cases with descending adjacent timestamps.
Alternative (activity, lifecycle) variant count: 16,692.
Observed event span (UTC): 2016-01-01T09:51:15.304000+00:00 to 2017-02-01T14:11:03.499000+00:00.
