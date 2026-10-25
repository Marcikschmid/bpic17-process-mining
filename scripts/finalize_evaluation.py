"""Explicitly refresh the selected quality assets after a complete HM run.

This separate command selects the same three report assets already used in the
report. Ordinary evaluation/rendering commands never write into report/.
"""

import argparse
import ctypes
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def wait_for_process(pid):
    """Wait on a Windows process handle, without a deadline or PID-reuse race."""
    from ctypes import wintypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    handle = kernel.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE only
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        while True:
            result = kernel.WaitForSingleObject(handle, 60_000)
            if result == 0:
                return
            if result != 258:  # WAIT_TIMEOUT means still running, not an error
                raise ctypes.WinError(ctypes.get_last_error())
            print(f"Waiting for alignment process {pid}; no time limit", flush=True)
    finally:
        kernel.CloseHandle(handle)


def require_complete(root):
    for model in ("inductive_miner", "heuristics_miner"):
        path = root / f"results/tables/evaluation/{model}_alignment.json"
        result = json.loads(path.read_text(encoding="utf-8"))
        if (result.get("status") != "ok" or not isinstance(result.get("cases"), int)
                or result["cases"] <= 0 or result.get("evaluated_cases") != result["cases"]):
            raise ValueError(f"{model}: complete alignment fitness is required before finalization")


def finalize(root=ROOT):
    require_complete(root)
    for script, arguments in (("evaluate_models.py", ["--summarize"]),
                              ("render_evaluation.py", []),
                              ("verify_evaluation.py", [])):
        subprocess.run([sys.executable, str(root / "scripts" / script), *arguments],
                       cwd=root, check=True)
    selected = ["figures/quality_comparison.pdf", "figures/simplicity_comparison.pdf",
                "tables/quality_metrics.tex"]
    for relative in selected:
        source, target = root / "results" / relative, root / "report" / relative
        shutil.copyfile(source, target)
        if hashlib.sha256(source.read_bytes()).digest() != hashlib.sha256(target.read_bytes()).digest():
            raise ValueError(f"Report copy differs: {relative}")
    shell = shutil.which("pwsh") or shutil.which("powershell")
    if shell is None:
        raise RuntimeError("PowerShell is required for the report build")
    subprocess.run([shell, "-NoProfile", "-File", str(root / "report/build.ps1")],
                   cwd=root, check=True)
    log = (root / "report/build/main.log").read_text(encoding="utf-8", errors="replace")
    if "Overfull \\hbox" in log or "There were undefined references" in log:
        raise ValueError("Report build has layout/reference warnings; review main.log")
    metrics = json.loads((root / "results/tables/quality_metrics.json").read_text(encoding="utf-8"))
    hm = metrics["models"]["heuristics_miner"]["alignment"]
    path = root / "docs/EVALUATION.md"
    text = path.read_text(encoding="utf-8")
    start, end = text.index("**Stand:**"), text.index("## Eingabe und Abgrenzung")
    text = text[:start] + (
        "**Stand:** Die vier Qualitätsdimensionen und die optimale Alignment-Fitness "
        "sind für beide Modelle vollständig berechnet. Der zusätzliche HM-Lauf "
        f"ohne weitere Zeitgrenze umfasst alle {hm['evaluated_cases']:,} Fälle "
        f"(Log-Fitness {hm['fitness']['log_fitness']:.8f}; "
        f"{hm['fitting_cases']:,} passende Fälle). Der strenge Audit ist bestanden. "
        "Frühere begrenzte Läufe sind nur als Berechnungshistorie dokumentiert.\n\n"
    ) + text[end:]
    path.write_text(text, encoding="utf-8", newline="\n")
    path = root / "docs/CHECKLIST.md"
    text = path.read_text(encoding="utf-8").replace(
        "zusätzliche HM-Alignment-Fitness mit dokumentierter Berechnungslücke.",
        "zusätzliche optimale HM-Alignment-Fitness vollständig berechnet.").replace(
        "- [ ] Zusätzliche optimale HM-Alignment-Fitness vollständig berechnen (kein Mittelwert über Teilergebnisse; bisherige Laufgrenzen dokumentiert).",
        "- [x] Zusätzliche optimale HM-Alignment-Fitness für alle Fälle ohne weitere Zeitgrenze berechnen; strenger Audit bestanden.")
    path.write_text(text, encoding="utf-8", newline="\n")
    path = root / "docs/AI_USAGE.md"
    text = path.read_text(encoding="utf-8").replace(
        "bestehende Kennzahlen erhalten | Laufend |",
        "bestehende Kennzahlen erhalten; vollständige HM-Auswertung abschließen, "
        "Tabellen/Grafiken aktualisieren, strengen Audit und Reportbuild ausführen | Offen |")
    path.write_text(text, encoding="utf-8", newline="\n")
    return {"status": "ok", "completed_utc": datetime.now(timezone.utc).isoformat(),
            "all_alignment_fitness_values_available": True,
            "strict_verification_passed": True, "report_built": True,
            "selected_report_assets": selected, "new_pdf_visual_review_pending": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wait-pid", type=int, help="Wait for this alignment worker; no deadline.")
    args = parser.parse_args()
    output = ROOT / "tmp/evaluation/finalization_status.json"
    try:
        if args.wait_pid:
            wait_for_process(args.wait_pid)
        result = finalize()
    except Exception as error:
        result = {"status": "error", "error_type": type(error).__name__, "reason": str(error)}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result, indent=2), flush=True)
    if result["status"] != "ok":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
