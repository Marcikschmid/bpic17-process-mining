"""The business-rule check finds violations in the model language and counts log counterexamples."""

import unittest

import pm4py

from src.domain_rules import log_counterexamples, model_violations, rule_name
from src.tree_edits_domain import DOMAIN, build_tree, parse

APPROVAL_AFTER_RETURN = rule_name("A_Pending", ("O_Returned",))


def violations(tree):
    return model_violations(*pm4py.convert_to_petri_net(parse(tree)))


class DomainRuleTests(unittest.TestCase):
    def test_detects_approval_without_returned_offer(self):
        found = violations("->( 'A_Accepted', 'O_Create Offer', 'O_Sent (mail and online)', "
                           "X( tau, ->( 'O_Returned', 'A_Validating' ) ), 'A_Pending' )")
        self.assertIn(APPROVAL_AFTER_RETURN, found)
        self.assertEqual(found[APPROVAL_AFTER_RETURN][-1], "A_Pending")

    def test_accepts_model_that_keeps_the_order(self):
        found = violations("->( 'A_Accepted', 'O_Create Offer', 'O_Sent (mail and online)', 'O_Returned', "
                           "'A_Validating', X( 'A_Pending', ->( 'A_Denied', 'O_Refused' ) ) )")
        self.assertEqual(found, {})

    def test_detects_two_outcomes(self):
        found = violations("->( 'A_Denied', 'O_Refused', 'A_Cancelled' )")
        self.assertIn("at most one outcome", found)

    def test_log_counterexamples(self):
        counts = log_counterexamples([("O_Sent (online only)", "O_Returned", "A_Validating", "A_Pending"),
                                      ("A_Validating", "A_Pending")])
        self.assertEqual(counts[APPROVAL_AFTER_RETURN], 1)
        self.assertEqual(counts["at most one outcome"], 0)

    def test_domain_model_keeps_all_rules_and_r2_breaks_one(self):
        self.assertEqual(violations(build_tree(DOMAIN)), {})
        self.assertIn(APPROVAL_AFTER_RETURN, violations(build_tree(DOMAIN + ("R2",))))


if __name__ == "__main__":
    unittest.main()
