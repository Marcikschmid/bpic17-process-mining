"""Exercise real alignment export and prevent silently biased partial averages."""

import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import evaluate_models as evaluation
from pm4py.objects.petri_net.obj import PetriNet, Marking
from pm4py.objects.petri_net.utils.petri_utils import add_arc_from_to
from pm4py.algo.conformance.alignments.petri_net import algorithm as alignment
from src import alignment as checkpoint_alignment


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(dir=evaluation.ROOT / "tmp")
        self.root = Path(self.directory.name)
        for relative in ("scripts/evaluate_models.py", "src/simplicity.py", "src/discovery.py", "src/quality.py", "src/alignment.py"):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(evaluation.ROOT / relative, path)
        net = PetriNet("sequence")
        start, end = PetriNet.Place("i"), PetriNet.Place("o")
        transition = PetriNet.Transition("a", "A")
        net.places.update([start, end])
        net.transitions.add(transition)
        add_arc_from_to(start, transition, net)
        add_arc_from_to(transition, end, net)
        model = self.root / "results/models/inductive_miner.pnml"
        model.parent.mkdir(parents=True)
        evaluation.pm4py.write_pnml(net, Marking({start: 1}), Marking({end: 1}), str(model))
        manifest = {"models": {"inductive_miner": {"artifacts": {
            "results/models/inductive_miner.pnml": {"sha256": evaluation.sha256(model)}}}}}
        evaluation.write_json(self.root / "results/tables/discovery_manifest.json", manifest)
        self.cache = self.root / "cache.json"
        evaluation.write_json(self.cache, {"raw_sha256": "test", "projection": {
            "discovery_cases": 2, "discovery_events": 2}, "traces": [
                {"case_id": "first", "activities": ["A"]},
                {"case_id": "second", "activities": ["A"]}]})

    def tearDown(self):
        self.directory.cleanup()

    def run_alignment(self, workers=None, force=False):
        with patch.multiple(evaluation, ROOT=self.root, CACHE=self.cache,
                            TABLES=self.root / "results/tables/evaluation"), contextlib.redirect_stdout(io.StringIO()):
            evaluation.worker("inductive_miner", "alignment", alignment_workers=workers, force=force)
        return json.loads((self.root / "results/tables/evaluation/inductive_miner_alignment.json").read_text())

    def test_alignment_export_retains_case_multiplicity_and_serializable_parameters(self):
        # Runs actual PM4Py A*: it mutates its parameters with Enum keys.
        result = self.run_alignment()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["variants"], 1)
        self.assertEqual(result["evaluated_cases"], 2)
        self.assertEqual(result["fitting_cases"], 2)
        self.assertEqual(result["fitness"]["log_fitness"], 1)
        self.assertNotIn("max_align_time_trace", result["parameters"])
        self.assertIsNone(result["time_limit_seconds"])
        self.assertTrue(all(isinstance(k, str) for k in result["parameters"]))

    def test_missing_alignment_never_receives_a_subset_fitness(self):
        cached = json.loads(self.cache.read_text())
        cached["traces"][1]["activities"] = ["X"]
        evaluation.write_json(self.cache, cached)
        with patch.object(checkpoint_alignment, "_compute", side_effect=[{"fitness": 1, "cost": 0, "bwc": 20000}, None]):
            result = self.run_alignment()
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["evaluated_cases"], 1)
        self.assertIsNone(result["fitness"])
        self.assertNotIn("fitting_cases", result)
        # An incomplete result must not block a later complete computation.
        resumed = self.run_alignment()
        self.assertEqual(resumed["status"], "ok")
        self.assertEqual(resumed["reused_case_alignments"], 1)

    def test_reuses_only_a_successful_matching_result(self):
        original = self.run_alignment()
        with patch.object(checkpoint_alignment, "_compute", side_effect=AssertionError("Should reuse the complete result")):
            reused = self.run_alignment()
        self.assertEqual(reused, original)

    def test_two_alignment_workers_preserve_fitness_and_case_multiplicity(self):
        result = self.run_alignment(workers=2)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["evaluated_cases"], 2)
        self.assertEqual(result["fitting_cases"], 2)
        self.assertEqual(result["fitness"]["log_fitness"], 1)
        self.assertTrue(result["parameters"]["multiprocessing"])
        self.assertEqual(result["parameters"]["cores"], 2)

    def test_mixed_variants_have_identical_weighted_sequential_and_parallel_scores(self):
        cached = json.loads(self.cache.read_text())
        cached["traces"].append({"case_id": "nonfitting", "activities": ["X"]})
        cached["projection"] = {"discovery_cases": 3, "discovery_events": 3}
        evaluation.write_json(self.cache, cached)
        sequential = self.run_alignment(workers=1)
        parallel = self.run_alignment(workers=2, force=True)
        for result in (sequential, parallel):
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["variants"], 2)
            self.assertEqual(result["evaluated_cases"], 3)
            self.assertEqual(result["fitting_cases"], 2)
            self.assertAlmostEqual(result["fitness"]["log_fitness"], 2 / 3)
            self.assertAlmostEqual(result["fitness"]["percFitTraces"], 200 / 3)
        self.assertEqual(sequential["fitness"], parallel["fitness"])

    def test_resume_keeps_finished_variants_after_interruption(self):
        cached = json.loads(self.cache.read_text())
        cached["traces"][1]["activities"] = ["X"]
        evaluation.write_json(self.cache, cached)
        with patch.object(checkpoint_alignment, "_compute", side_effect=[
                {"fitness": 1, "cost": 0, "bwc": 20000}, RuntimeError("interrupted")]):
            failed = self.run_alignment()
        self.assertEqual(failed["status"], "error")
        self.assertEqual(len(list((self.root / "tmp/evaluation/inductive_miner_variants").glob("*.json"))), 1)
        resumed = self.run_alignment()
        self.assertEqual(resumed["status"], "ok")
        self.assertEqual(resumed["reused_case_alignments"], 1)
        self.assertEqual(resumed["evaluated_cases"], 2)

    def test_tau_costs_and_weighted_scores_match_original_pm4py(self):
        # Tau costs must remain 1, even though trace fitness rounds them away.
        model = self.root / "results/models/inductive_miner.pnml"
        net, initial, final = evaluation.pm4py.read_pnml(str(model))
        old_end = next(iter(final))
        end = PetriNet.Place("new_end")
        tau = PetriNet.Transition("tau", None)
        net.places.add(end)
        net.transitions.add(tau)
        add_arc_from_to(old_end, tau, net)
        add_arc_from_to(tau, end, net)
        final = Marking({end: 1})
        evaluation.pm4py.write_pnml(net, initial, final, str(model))
        manifest = {"models": {"inductive_miner": {"artifacts": {
            "results/models/inductive_miner.pnml": {"sha256": evaluation.sha256(model)}}}}}
        evaluation.write_json(self.root / "results/tables/discovery_manifest.json", manifest)
        cached = json.loads(self.cache.read_text())
        cached["traces"].append({"case_id": "nonfitting", "activities": ["X"]})
        cached["projection"] = {"discovery_cases": 3, "discovery_events": 3}
        evaluation.write_json(self.cache, cached)
        from pm4py.algo.evaluation.replay_fitness.variants import alignment_based
        with patch.object(evaluation, "CACHE", self.cache):
            log, _ = evaluation.read_log()
        reference = alignment.apply_log(log, net, initial, final,
            parameters=dict(evaluation.PARAMETERS),
            variant=alignment.Variants.VERSION_STATE_EQUATION_A_STAR)
        streamed = self.run_alignment(workers=2)
        self.assertEqual(streamed["fitness"], alignment_based.evaluate(reference))
        checkpoints = list((self.root / "tmp/evaluation/inductive_miner_variants").glob("*.json"))
        for path in checkpoints:
            item = json.loads(path.read_text())
            expected = reference[0 if item["activities"] == ["A"] else 2]
            self.assertEqual(item["alignment"]["cost"], expected["cost"])
            self.assertEqual(item["alignment"]["bwc"], expected["bwc"])

    def test_checkpoint_identity_prevents_reuse_for_changed_input(self):
        self.run_alignment()
        cached = json.loads(self.cache.read_text())
        cached["traces"][0]["case_id"] = "different-input"
        evaluation.write_json(self.cache, cached)
        resumed = self.run_alignment()
        self.assertEqual(resumed["reused_case_alignments"], 0)
        self.assertEqual(resumed["status"], "ok")


if __name__ == "__main__":
    unittest.main()
