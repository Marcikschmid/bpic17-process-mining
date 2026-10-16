"""Load the unchanged BPIC-17 log with its case and event attributes."""

from pathlib import Path

from src.runtime import configure_runtime

configure_runtime()

import pm4py


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG = ROOT / "data" / "raw" / "BPI Challenge 2017.xes.gz"


def load_event_log(path=DEFAULT_LOG):
    """Return a PM4Py EventLog, without filtering events or lifecycle states."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(
            f"Missing event log: {path}. Run scripts/download_data.py first."
        )
    return pm4py.read_xes(
        str(path), variant="iterparse", return_legacy_log_object=True
    )
