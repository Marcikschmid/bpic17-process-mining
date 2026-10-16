"""Check imports, native Graphviz rendering, plotting and the notebook kernel."""

import json
import platform
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.runtime import configure_runtime


def main():
    dot = configure_runtime()
    if dot is None:
        raise RuntimeError("Graphviz is missing. Run scripts/setup_graphviz.py.")
    import graphviz
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import nbformat
    import pandas
    import pm4py
    import sklearn
    from jupyter_client.kernelspec import KernelSpecManager

    packages = {
        name: version(name)
        for name in ("pm4py", "pandas", "matplotlib", "scikit-learn", "jupyterlab", "ipykernel")
    }
    svg = graphviz.Source("digraph { start -> end }").pipe(format="svg")
    if b"<svg" not in svg:
        raise RuntimeError("Graphviz did not produce an SVG.")
    cache = ROOT / "tmp" / "setup-check"
    cache.mkdir(parents=True, exist_ok=True)
    figure, axes = plt.subplots()
    axes.plot([0, 1], [0, 1])
    figure.savefig(cache / "plot.png")
    plt.close(figure)
    notebook = nbformat.read(ROOT / "notebooks" / "01_getting_started.ipynb", as_version=4)
    nbformat.validate(notebook)
    kernels = KernelSpecManager().find_kernel_specs()
    if "bpic17" not in kernels:
        raise RuntimeError("The local bpic17 notebook kernel is missing.")
    print(json.dumps({
        "python": platform.python_version(),
        "packages": packages,
        "graphviz": subprocess.check_output([dot, "-V"], stderr=subprocess.STDOUT, text=True).strip(),
        "checks": ["imports", "Graphviz SVG rendering", "matplotlib PNG rendering", "notebook format", "bpic17 kernel registered"],
    }, indent=2))


if __name__ == "__main__":
    main()
