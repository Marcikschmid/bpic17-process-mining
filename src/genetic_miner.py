"""Third discovery experiment using the installed PM4Py CLASSIC Genetic Miner."""
GENETIC_PARAMETERS = {
    "population_size": 10,
    "elitism_rate": 0.1,
    "crossover_rate": 1.0,
    "mutation_rate": 0.01,
    "generations": 6,
    "elitism_min_sample": 2,
    "activity_key": "concept:name",
    "timestamp_key": "time:timestamp",
    "case_id_key": "case:concept:name",
}
DEFAULT_SEED = 20261025


def discover_genetic(frame, seed=DEFAULT_SEED, log_csv=None, **overrides):
    import random
    import numpy as np
    import pm4py
    parameters={**GENETIC_PARAMETERS,**overrides}
    if parameters["population_size"]<2 or parameters["generations"]<1:
        raise ValueError("At least two individuals and one generation required")
    if not 1<=parameters["elitism_min_sample"]<parameters["population_size"]:
        raise ValueError("Tournament sample must fit the population")
    for key in ("elitism_rate","crossover_rate","mutation_rate"):
        if not 0<=parameters[key]<=1:raise ValueError(f"Invalid rate: {key}")
    random.seed(seed);np.random.seed(seed)
    return pm4py.discover_petri_net_genetic(frame,log_csv=log_csv,**parameters)
