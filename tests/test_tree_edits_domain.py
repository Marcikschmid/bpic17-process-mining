"""Domain edits reproduce the work-item base and encode the intended business rules."""

import unittest

import pm4py

from src.replay_coverage import ExactReplay
from src.tree_edits_domain import BASE, DOMAIN, EDITS, SCREENED, build_tree, combinations, parse

START = ("A_Create Application", "A_Concept", "A_Accepted", "O_Create Offer", "O_Sent (mail and online)",
         "W_Call after offers", "A_Complete")
ROUND = ("O_Returned", "W_Validate application", "A_Validating")
WORK_ITEMS = {"W_Assess potential fraud", "W_Call after offers", "W_Call incomplete files", "W_Complete application",
              "W_Handle leads", "W_Personal Loan collection", "W_Shortened completion ", "W_Validate application"}


def fits(active, trace):
    machine = ExactReplay(*pm4py.convert_to_petri_net(parse(build_tree(active))))
    coverage, _ = machine.evaluate([tuple(trace)])
    return coverage["fitting_cases"] == 1


def labels(active):
    net = pm4py.convert_to_petri_net(parse(build_tree(active)))[0]
    return {t.label for t in net.transitions if t.label is not None}


class DomainEditTests(unittest.TestCase):
    def test_base_is_the_template_without_edits(self):
        self.assertEqual(build_tree(()), BASE)
        self.assertTrue({"W_Handle leads", "W_Complete application", "W_Call after offers",
                         "W_Validate application", "W_Call incomplete files"} <= labels(()))

    def test_stages_partition_the_edits(self):
        self.assertEqual(set(DOMAIN) | set(SCREENED), set(EDITS))
        self.assertFalse(set(DOMAIN) & set(SCREENED))
        self.assertTrue(all(EDITS[e]["stage"] == "domain" for e in DOMAIN))
        self.assertEqual(len(list(combinations(SCREENED))), 2 ** len(SCREENED))
        with self.assertRaises(ValueError):
            build_tree(("R3",))

    def test_domain_model_contains_every_work_item(self):
        self.assertEqual({label for label in labels(DOMAIN) if label.startswith("W_")}, WORK_ITEMS)

    def test_d1_forbids_approval_without_validation_but_keeps_early_denial(self):
        approved_unvalidated = START + ("A_Pending",)
        denied_early = START + ("A_Denied", "O_Refused")
        approved = START + ROUND + ("A_Pending",)
        self.assertTrue(fits((), approved_unvalidated))
        self.assertFalse(fits(("D1",), approved_unvalidated))
        self.assertTrue(fits(("D1",), denied_early))
        self.assertTrue(fits(("D1",), approved))

    def test_rare_steps_are_added_by_their_edits(self):
        fraud = START + ROUND + ("W_Assess potential fraud", "A_Denied", "O_Refused")
        online = ("A_Create Application", "A_Concept", "A_Accepted", "O_Create Offer", "O_Sent (online only)",
                  "W_Call after offers", "A_Complete", "A_Cancelled")
        shortened = ("A_Create Application", "W_Shortened completion ", "A_Concept") + START[2:] + ("A_Cancelled",)
        collection = START + ROUND + ("A_Pending", "W_Personal Loan collection")
        for edit, trace in (("D2", fraud), ("G1", online), ("D4", shortened), ("D5", collection)):
            self.assertFalse(fits((), trace), edit)
            self.assertTrue(fits((edit,), trace), edit)

    def test_domain_model_is_sound(self):
        net, initial, final = pm4py.convert_to_petri_net(parse(build_tree(DOMAIN)))
        self.assertTrue(pm4py.check_soundness(net, initial, final)[0])


if __name__ == "__main__":
    unittest.main()
