"""Prevent publishing partial alignment results through the finalization step."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.finalize_evaluation import finalize, require_complete


class FinalizationTests(unittest.TestCase):
    def test_incomplete_alignment_blocks_all_export_and_build_commands(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / "results/tables/evaluation"
            directory.mkdir(parents=True)
            for model in ("inductive_miner", "heuristics_miner"):
                (directory / f"{model}_alignment.json").write_text(json.dumps({
                    "status": "ok" if model == "inductive_miner" else "incomplete",
                    "cases": 3, "evaluated_cases": 3 if model == "inductive_miner" else 2}))
            with patch("scripts.finalize_evaluation.subprocess.run") as run:
                with self.assertRaises(ValueError):
                    finalize(root)
                run.assert_not_called()

    def test_missing_case_counts_cannot_appear_complete(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / "results/tables/evaluation"
            directory.mkdir(parents=True)
            (directory / "inductive_miner_alignment.json").write_text('{"status": "ok"}')
            with self.assertRaises(ValueError):
                require_complete(root)


if __name__ == "__main__":
    unittest.main()
