"""Regression tests for deterministic policy guardrails."""
import unittest
from datetime import date, timedelta

from agent import enforce_policy_guardrails, _is_unresolved_entity


def _base_memo() -> dict:
    return {
        "entity_name": "Example Co",
        "domain": "example.com",
        "verdict": "PROCEED",
        "confidence": 0.9,
        "summary": "Looks healthy.",
        "evidence": [
            {"severity": "POSITIVE", "field": "operating_status", "finding": "Active", "raw_value": "active"},
            {"severity": "POSITIVE", "field": "growth_stage", "finding": "Late stage", "raw_value": "late_stage"},
            {"severity": "NEUTRAL", "field": "employee_count", "finding": "Stable headcount", "raw_value": "300"},
        ],
        "requires_human_review": False,
        "review_reason": None,
    }


def _base_profile() -> dict:
    return {
        "operating_status": "active",
        "growth_stage": "late_stage",
        "founded_year": 2018,
        "employee_count": 300,
        "investor_count": 5,
        "highlights": ["top_tier_investors"],
        "funding": {"last_funding_date": str(date.today() - timedelta(days=120))},
        "headcount_12mo_change_pct": 8,
    }


class PolicyGuardrailsTest(unittest.TestCase):
    def test_declines_closed_company(self) -> None:
        memo = _base_memo()
        profile = _base_profile()
        profile["operating_status"] = "closed"
        out = enforce_policy_guardrails(memo, profile)
        self.assertEqual(out["verdict"], "DECLINE")
        self.assertFalse(out["requires_human_review"])

    def test_declines_tiny_new_company_with_no_investors(self) -> None:
        memo = _base_memo()
        profile = _base_profile()
        profile["founded_year"] = date.today().year
        profile["employee_count"] = 2
        profile["investor_count"] = 0
        out = enforce_policy_guardrails(memo, profile)
        self.assertEqual(out["verdict"], "DECLINE")

    def test_escalates_acquired_company(self) -> None:
        memo = _base_memo()
        profile = _base_profile()
        profile["operating_status"] = "acquired"
        out = enforce_policy_guardrails(memo, profile)
        self.assertEqual(out["verdict"], "ESCALATE")
        self.assertTrue(out["requires_human_review"])
        self.assertIn("acquired", (out["review_reason"] or "").lower())

    def test_escalates_no_recent_funding_and_negative_headcount(self) -> None:
        memo = _base_memo()
        profile = _base_profile()
        profile["highlights"] = ["no_recent_funding"]
        profile["funding"]["last_funding_date"] = str(date.today() - timedelta(days=365 * 4))
        profile["headcount_12mo_change_pct"] = -12
        out = enforce_policy_guardrails(memo, profile)
        self.assertEqual(out["verdict"], "ESCALATE")
        self.assertTrue(out["requires_human_review"])

    def test_escalates_mixed_strong_signals(self) -> None:
        memo = _base_memo()
        profile = _base_profile()
        profile["highlights"] = ["top_tier_investors", "no_recent_funding"]
        profile["headcount_12mo_change_pct"] = -5
        profile["funding"]["last_funding_date"] = str(date.today() - timedelta(days=120))
        out = enforce_policy_guardrails(memo, profile)
        self.assertEqual(out["verdict"], "ESCALATE")

    def test_escalates_low_confidence(self) -> None:
        memo = _base_memo()
        memo["confidence"] = 0.4
        out = enforce_policy_guardrails(memo, _base_profile())
        self.assertEqual(out["verdict"], "ESCALATE")
        self.assertTrue(out["requires_human_review"])

    def test_applies_confidence_penalties_for_missing_fields(self) -> None:
        memo = _base_memo()
        profile = _base_profile()
        profile["operating_status"] = None
        profile["growth_stage"] = None
        profile["employee_count"] = None
        profile["funding"]["last_funding_date"] = None
        profile["highlights"] = []
        out = enforce_policy_guardrails(memo, profile)
        self.assertEqual(out["confidence"], 0.35)

    def test_no_profile_keeps_original_memo(self) -> None:
        memo = _base_memo()
        out = enforce_policy_guardrails(memo, None)
        self.assertEqual(out["verdict"], "PROCEED")
        self.assertEqual(out["confidence"], 0.9)


class UnresolvedEntityPolicyTest(unittest.TestCase):
    def test_no_domain_match_forces_decline(self) -> None:
        trace = [{"tool": "search_company", "result_preview": '{"domain": null}'}]
        self.assertTrue(_is_unresolved_entity(trace, None))

    def test_resolved_or_enriched_entity_is_not_unresolved(self) -> None:
        trace = [{"tool": "search_company", "result_preview": '{"domain": "example.com"}'}]
        self.assertFalse(_is_unresolved_entity(trace, None))
        self.assertFalse(_is_unresolved_entity(trace, {"operating_status": "active"}))


if __name__ == "__main__":
    unittest.main()
