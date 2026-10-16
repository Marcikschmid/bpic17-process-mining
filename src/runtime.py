"""Configure only this Python process to use the project's Graphviz."""

import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def configure_runtime():
    # Keep generated plotting configuration inside the ignored project cache.
    cache = ROOT / "tmp" / "matplotlib"
    cache.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(cache))
    local_graphviz = ROOT / ".tools" / "graphviz"
    if local_graphviz.is_dir():
        executables = list(local_graphviz.rglob("dot.exe"))
        if len(executables) == 1:
            directory = str(executables[0].parent)
            if directory not in os.environ.get("PATH", "").split(os.pathsep):
                os.environ["PATH"] = directory + os.pathsep + os.environ.get("PATH", "")
    return shutil.which("dot")
