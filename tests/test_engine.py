from __future__ import annotations

import copy
from decimal import Decimal
from pathlib import Path
import tempfile
import unittest

import bootstrap  # noqa: F401
from xactimate_reconcile.contracts import digest, load_json, money
from xactimate_reconcile.engine import reconcile, review_subjects
from core_fixture import make_case


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_contract_helpers_are_strict_and_deterministic(self):
        self.assertEqual(money(Decimal("1.005")), "1.01")
        self.assertEqual(digest({"b": "é", "a": 1}), digest({"a": 1, "b": "é"}))
        duplicate = self.tmp_path / "duplicate.json"
        duplicate.write_text('{"a": 1, "a": 2}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Duplicate JSON key"):
            load_json(duplicate)
        nonfinite = self.tmp_path / "nonfinite.json"
        nonfinite.write_text('{"a": NaN}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Nonfinite"):
            load_json(nonfinite)

    def test_complete_case_computes_independent_expected_arithmetic(self):
        case, source_root = make_case(self.tmp_path)
        before = copy.deepcopy(case)
        report = reconcile(case, source_root)
        self.assertEqual(case, before)
        self.assertEqual(report["schema_version"], "xr-report/1.0")
        self.assertEqual(report["status"], "draft")
        self.assertIs(report["release_allowed"], False)
        self.assertEqual(report["groups"][0]["components"], {
            "quantity": "20.00", "price": "12.00", "scope": "0.00",
            "specification_bundle": "0.00", "bundle": "0.00", "rounding": "0.00",
        })
        self.assertEqual(report["totals"], {
            "baseline_direct": "100.00", "proposed_direct": "132.00",
            "delta_direct": "32.00", "upward_changes": "32.00",
            "downward_changes": "0.00", "unchanged_groups": 0,
        })
        self.assertEqual(report["partial_totals"]["supported_delta"], "32.00")

    def test_unknown_number_holds_only_affected_group_and_preserves_partial_shape(self):
        case, source_root = make_case(self.tmp_path)
        case["lines"][1]["quantity"].update(
            value=None, raw_text="?", alternatives=["12", "72"], resolution=None,
            verification="ambiguous",
        )
        report = reconcile(case, source_root)
        self.assertEqual(report["status"], "partial")
        self.assertIsNone(report["totals"])
        self.assertEqual(report["groups"][0]["status"], "held")
        self.assertIsNone(report["groups"][0]["delta"])
        self.assertEqual(report["partial_totals"], {"supported_delta": None, "is_complete": False})
        self.assertIn("line:P-1:quantity", report["review_summary"]["pending_subjects"])

    def test_source_side_must_match_line_side(self):
        case, source_root = make_case(self.tmp_path)
        case["lines"][0]["quantity"]["source"]["doc_id"] = "DOC-P"
        report = reconcile(case, source_root)
        self.assertEqual(report["status"], "blocked")
        self.assertTrue(any(issue["code"] == "E_SOURCE_SIDE" for issue in report["issues"]))

    def test_unexpected_root_field_is_rejected(self):
        case, source_root = make_case(self.tmp_path)
        case["pretend_release_approved"] = True
        report = reconcile(case, source_root)
        self.assertEqual(report["status"], "blocked")
        self.assertTrue(any(issue["code"] == "E_SCHEMA" for issue in report["issues"]))

    def test_malformed_page_values_return_actionable_issue_without_internal_error(self):
        case, source_root = make_case(self.tmp_path)
        case["lines"][0]["source"]["page"] = None
        report = reconcile(case, source_root)
        self.assertEqual(report["status"], "blocked")
        self.assertTrue(any(issue["code"] == "E_SOURCE_REF" for issue in report["issues"]))
        self.assertFalse(any(issue["code"] == "E_INPUT" for issue in report["issues"]))

    def test_malformed_document_page_count_does_not_escape_validator(self):
        case, source_root = make_case(self.tmp_path)
        case["documents"][0]["page_count"] = "one"
        report = reconcile(case, source_root)
        self.assertEqual(report["status"], "blocked")
        self.assertTrue(any(issue["code"] == "E_SCHEMA" for issue in report["issues"]))
        self.assertFalse(any(issue["code"] == "E_INPUT" for issue in report["issues"]))

    def test_nested_wrong_json_types_do_not_trigger_internal_error(self):
        mutations = [
            lambda c: c["groups"][0]["scope_support"].update(source_ids=[{}]),
            lambda c: c["groups"][0]["coverage"].update(source_ids=[{}]),
            lambda c: c["financial_adjustments"]["proposed"].append({
                "id": "fee", "label": "Fee", "kind": "fee", "method": "amount",
                "amount": copy.deepcopy(c["lines"][1]["quantity"]), "rate": None,
                "basis": ["direct"], "evidence_ids": [{}],
            }),
        ]
        for index, mutation in enumerate(mutations):
            with self.subTest(mutation=mutation):
                case, source_root = make_case(self.tmp_path / str(index))
                mutation(case)
                report = reconcile(case, source_root)
                self.assertEqual(report["status"], "blocked")
                self.assertFalse(any(issue["code"] == "E_INPUT" for issue in report["issues"]))

        case, source_root = make_case(self.tmp_path / "review")
        subject = next(iter(review_subjects(case)))
        reviews = [{"subject": [], "fingerprint": subject, "decision": "confirm", "kind": "human",
                    "reviewer": "Reviewer", "reviewed_at": "2026-09-21T13:00:00Z"}]
        report = reconcile(case, source_root, reviews)
        self.assertTrue(any(issue["code"] == "R_REVIEW_SUBJECT" for issue in report["issues"]))
        self.assertFalse(any(issue["code"] == "E_INPUT" for issue in report["issues"]))

    def test_review_fingerprint_invalidates_after_document_version_edit(self):
        case, _ = make_case(self.tmp_path)
        first = review_subjects(case)["line:B-1:quantity"]["fingerprint"]
        case["documents"][0]["version"] = "v2"
        second = review_subjects(case)["line:B-1:quantity"]["fingerprint"]
        self.assertNotEqual(first, second)

    def test_latest_exact_human_confirmation_and_stale_review_are_reported(self):
        case, source_root = make_case(self.tmp_path)
        subjects = review_subjects(case)
        subject = "line:B-1:quantity"
        reviews = [{
            "subject": subject, "fingerprint": subjects[subject]["fingerprint"], "decision": "confirm",
            "kind": "human", "reviewer": "A. Reviewer", "reviewed_at": "2026-09-21T13:00:00Z",
        }]
        confirmed = reconcile(case, source_root, reviews)
        self.assertIn(subject, confirmed["review_summary"]["human_confirmed"])
        case["documents"][0]["version"] = "v2"
        stale = reconcile(case, source_root, reviews)
        self.assertIn(subject, stale["review_summary"]["stale_subjects"])
        self.assertIn(subject, stale["review_summary"]["pending_subjects"])

    def test_credit_line_uses_negative_total_with_nonnegative_inputs(self):
        case, source_root = make_case(self.tmp_path)
        credit = copy.deepcopy(case["lines"][1])
        credit.update(id="P-CREDIT", kind="credit", description="Synthetic credit")
        credit["quantity"]["value"] = credit["quantity"]["raw_text"] = "1"
        credit["unit_price"]["value"] = credit["unit_price"]["raw_text"] = "10"
        credit["reported_total"]["value"] = credit["reported_total"]["raw_text"] = "-10.00"
        case["lines"] = [credit]
        case["groups"][0].update(baseline=[], proposed=["P-CREDIT"], change_type="scope", absence_verified=True)
        case["documents"][0]["reported_direct_total"]["value"] = "0.00"
        case["documents"][0]["reported_direct_total"]["raw_text"] = "0.00"
        case["documents"][1]["reported_direct_total"]["value"] = "-10.00"
        case["documents"][1]["reported_direct_total"]["raw_text"] = "-10.00"
        report = reconcile(case, source_root)
        self.assertEqual(report["groups"][0]["delta"], "-10.00")
        self.assertEqual(report["totals"]["proposed_direct"], "-10.00")

    def test_credit_quantity_price_components_follow_signed_delta(self):
        case, source_root = make_case(self.tmp_path)
        for line in case["lines"]:
            line["kind"] = "credit"
            line["reported_total"]["value"] = "-100.00" if line["side"] == "baseline" else "-132.00"
            line["reported_total"]["raw_text"] = line["reported_total"]["value"]
        for doc in case["documents"][:2]:
            value = "-100.00" if doc["role"] == "baseline" else "-132.00"
            doc["reported_direct_total"]["value"] = value
            doc["reported_direct_total"]["raw_text"] = value
        report = reconcile(case, source_root)
        self.assertEqual(report["groups"][0]["components"]["quantity"], "-20.00")
        self.assertEqual(report["groups"][0]["components"]["price"], "-12.00")
        self.assertEqual(report["groups"][0]["components"]["rounding"], "0.00")

    def test_invalid_line_total_holds_group_and_supported_partial_total(self):
        case, source_root = make_case(self.tmp_path)
        case["lines"][1]["reported_total"]["value"] = "1320.00"
        case["lines"][1]["reported_total"]["raw_text"] = "1320.00"
        case["documents"][1]["reported_direct_total"]["value"] = "1320.00"
        case["documents"][1]["reported_direct_total"]["raw_text"] = "1320.00"
        report = reconcile(case, source_root)
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["groups"][0]["status"], "held")
        self.assertIsNone(report["partial_totals"]["supported_delta"])

    def test_ordered_financial_adjustments_report_exact_components(self):
        case, source_root = make_case(self.tmp_path)
        template = case["lines"][1]["quantity"]

        def field(value):
            item = copy.deepcopy(template)
            item["value"] = item["raw_text"] = value
            return item

        case["financial_adjustments"]["proposed"] = [
            {"id": "tax", "label": "Tax", "kind": "tax", "method": "rate", "amount": None,
             "rate": field("0.10"), "basis": ["direct"], "evidence_ids": ["EV-ROOF"]},
            {"id": "oh", "label": "Overhead", "kind": "overhead", "method": "rate", "amount": None,
             "rate": field("0.05"), "basis": ["direct", "tax"], "evidence_ids": ["EV-ROOF"]},
            {"id": "credit", "label": "Credit", "kind": "credit", "method": "amount", "amount": field("5"),
             "rate": None, "basis": ["direct"], "evidence_ids": ["EV-ROOF"]},
        ]
        report = reconcile(case, source_root)
        proposed = report["financial_bridge"]["proposed"]
        self.assertEqual([x["calculated"] for x in proposed["adjustments"]], ["13.20", "7.26", "-5.00"])
        self.assertEqual(proposed["total"], "147.46")
        self.assertIs(report["financial_bridge"]["baseline"]["adjustments_specified"], False)

    def test_noncredit_amount_adjustment_can_be_a_signed_correction(self):
        case, source_root = make_case(self.tmp_path)
        amount = copy.deepcopy(case["lines"][1]["quantity"])
        amount["value"] = amount["raw_text"] = "-2.50"
        case["financial_adjustments"]["proposed"] = [{
            "id": "fee-correction", "label": "Fee correction", "kind": "fee", "method": "amount",
            "amount": amount, "rate": None, "basis": ["direct"], "evidence_ids": ["EV-ROOF"],
        }]
        report = reconcile(case, source_root)
        self.assertEqual(report["financial_bridge"]["proposed"]["adjustments"][0]["calculated"], "-2.50")
        self.assertEqual(report["financial_bridge"]["proposed"]["total"], "129.50")

    def test_payment_scenario_keeps_net_payable_unknown(self):
        case, source_root = make_case(self.tmp_path)
        start = copy.deepcopy(case["lines"][1]["quantity"])
        start["value"] = start["raw_text"] = "1000"
        amount = copy.deepcopy(start)
        amount["value"] = amount["raw_text"] = "100"
        case["payment_scenario"] = {
            "label": "Synthetic arithmetic illustration", "start": start, "evidence_ids": ["EV-POLICY"],
            "policy_evidence_ids": ["EV-POLICY"],
            "steps": [{"id": "deductible", "label": "Synthetic deductible", "operation": "subtract",
                       "amount": amount, "evidence_ids": ["EV-POLICY"]}],
        }
        report = reconcile(case, source_root)
        self.assertEqual(report["financial_bridge"]["payment_scenario"]["result"], "900.00")
        self.assertIsNone(report["financial_bridge"]["payment_scenario"]["net_payable"])

    def test_unknown_payment_step_holds_scenario_instead_of_reusing_running_balance(self):
        case, source_root = make_case(self.tmp_path)
        start = copy.deepcopy(case["lines"][1]["quantity"])
        start["value"] = start["raw_text"] = "1000"
        amount = copy.deepcopy(start)
        amount.update(value=None, raw_text="?", alternatives=["100", "700"], resolution=None,
                      verification="ambiguous")
        case["payment_scenario"] = {
            "label": "Incomplete scenario", "start": start, "evidence_ids": ["EV-POLICY"],
            "policy_evidence_ids": ["EV-POLICY"],
            "steps": [{"id": "deductible", "label": "Unknown deductible", "operation": "subtract",
                       "amount": amount, "evidence_ids": ["EV-POLICY"]},
                      {"id": "supplement", "label": "Later addition", "operation": "add",
                       "amount": start, "evidence_ids": ["EV-POLICY"]}],
        }
        report = reconcile(case, source_root)
        scenario = report["financial_bridge"]["payment_scenario"]
        self.assertEqual(scenario["status"], "held")
        self.assertIsNone(scenario["result"])
        self.assertIsNotNone(scenario["reason"])
        self.assertIsNone(scenario["steps"][1]["before"])
        self.assertIsNone(scenario["steps"][1]["after"])

    def test_invalid_group_cannot_contribute_supported_partial_total(self):
        case, source_root = make_case(self.tmp_path)
        case["groups"][0]["proposed"] = ["NOT-A-LINE"]
        report = reconcile(case, source_root)
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["groups"][0]["status"], "held")
        self.assertIsNone(report["partial_totals"]["supported_delta"])

    def test_reused_lines_hold_every_affected_group(self):
        case, source_root = make_case(self.tmp_path)
        duplicate = copy.deepcopy(case["groups"][0])
        duplicate["claim_id"] = "C-002"
        case["groups"].append(duplicate)
        report = reconcile(case, source_root)
        self.assertEqual(report["status"], "blocked")
        self.assertTrue(all(group["status"] == "held" for group in report["groups"]))
        self.assertIsNone(report["partial_totals"]["supported_delta"])

    def test_any_hard_integrity_error_suppresses_all_computed_money(self):
        mutations = [
            lambda c: c["documents"][0].update(sha256="0" * 64),
            lambda c: c["groups"][0].update(roof_location="other-roof"),
            lambda c: c["groups"][0]["scope_support"].update(source_ids=["EV-MISSING"]),
            lambda c: c["lines"][1].update(unit="LF", area_basis="not_area"),
        ]
        for index, mutation in enumerate(mutations):
            with self.subTest(index=index):
                case, source_root = make_case(self.tmp_path / f"hard-{index}")
                mutation(case)
                report = reconcile(case, source_root)
                self.assertEqual(report["status"], "blocked")
                self.assertIsNone(report["totals"])
                self.assertIsNone(report["partial_totals"]["supported_delta"])
                self.assertTrue(all(group["status"] == "held" and group["delta"] is None
                                    and group["components"] is None for group in report["groups"]))


if __name__ == "__main__":
    unittest.main()
