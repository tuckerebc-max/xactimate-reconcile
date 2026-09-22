import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from prototype.reconcile import reconcile

ROOT = Path(__file__).resolve().parents[1]


class ReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.case = json.loads((ROOT / 'fixtures/synthetic_case.json').read_text())

    def run_case(self):
        return reconcile(self.case, ROOT / 'fixtures')

    def blocked(self, code):
        result = self.run_case()
        self.assertEqual('blocked', result['status'])
        self.assertFalse(result['release_allowed'])
        self.assertIsNone(result['totals'])
        self.assertIn(code, {x['code'] for x in result['issues']})

    def field(self, line, name, value):
        self.case['lines'][line][name]['value'] = value

    def retotal(self):
        # Fixture maintenance, not an oracle for expected reconciliation values.
        from decimal import Decimal
        for doc in self.case['documents'][:2]:
            total = sum(Decimal(x['reported_total']['value']) for x in self.case['lines'] if x['side'] == doc['role'])
            doc['reported_direct_total']['value'] = str(total)

    def test_positive_negative_and_unchanged_hand_calculated(self):
        r = self.run_case()
        self.assertEqual('draft', r['status'])
        self.assertEqual({'baseline_direct': '4650.00', 'proposed_direct': '5290.00', 'delta_direct': '640.00',
                          'upward_changes': '840.00', 'downward_changes': '-200.00', 'unchanged_groups': 2}, r['totals'])
        self.assertEqual('600.00', r['groups'][0]['components']['quantity'])
        self.assertEqual('240.00', r['groups'][0]['components']['price'])
        self.assertEqual('0.00', r['groups'][0]['components']['rounding'])
        self.assertFalse(r['release_allowed'])

    def test_carrier_correct_and_repair_feasible(self):
        r = self.run_case()
        self.assertEqual('draft', r['status'])
        g = next(g for g in r['groups'] if g['claim_id'] == 'C-003')
        self.assertEqual('0.00', g['delta'])
        self.assertEqual('retain_baseline', g['action'])
        self.assertEqual('repair_feasible', g['disposition'])

    def test_contractor_too_high_reduction(self):
        # Interpret the same supported reduction as correction of an overstated contractor draft.
        self.case['baseline_label'] = 'Contractor draft with overstated flashing'
        self.case['proposed_label'] = 'Reviewed correction'
        r = self.run_case()
        self.assertEqual('draft', r['status'])
        self.assertEqual('-200.00', r['groups'][1]['delta'])
        self.assertEqual('reduce', r['groups'][1]['action'])

    def test_sf_sq_equivalence(self):
        p = self.case['lines'][1]
        p['unit'] = 'SF'; p['quantity']['value'] = '1200'; p['unit_price']['value'] = '3.20'
        r = self.run_case()
        self.assertEqual('draft', r['status'])
        self.assertEqual('640.00', r['totals']['delta_direct'])

    def test_sf_sq_100_fold_error(self):
        self.case['lines'][1]['unit'] = 'SF'
        self.case['lines'][1]['unit_price']['value'] = '3.20'
        self.blocked('E_LINE_TOTAL')

    def test_incompatible_units(self):
        self.case['lines'][1]['unit'] = 'LF'
        self.case['lines'][1]['area_basis'] = 'not_area'
        self.blocked('E_UNIT')

    def test_blurry_digit_is_unknown(self):
        q = self.case['lines'][1]['quantity']
        q.update(value=None, alternatives=['12', '72'], verification='ambiguous', raw_text='?2')
        self.blocked('E_UNKNOWN')

    def test_high_ocr_confidence_cannot_replace_review(self):
        q = self.case['lines'][1]['quantity']
        q['verification'] = 'unreviewed'; q['ocr_confidence'] = '99.9'
        self.blocked('E_REVIEW')

    def test_unresolved_alternatives_block(self):
        self.case['lines'][1]['quantity']['alternatives'] = ['12', '72']
        self.blocked('E_AMBIGUOUS')

    def test_resolved_alternatives_retained(self):
        q = self.case['lines'][1]['quantity']
        q['alternatives'] = ['12', '72']; q['resolution'] = 'Fixture source reads 12; reviewed against original.'
        self.assertEqual('draft', self.run_case()['status'])

    def test_missing_pages(self):
        self.case['documents'][0]['page_count'] = 2
        self.blocked('E_INCOMPLETE')

    def test_declared_incomplete_estimate(self):
        self.case['documents'][0]['estimate_complete'] = False
        self.blocked('E_INCOMPLETE')

    def test_unit_price_line_total_disagree(self):
        self.field(1, 'reported_total', '3839.99')
        self.blocked('E_LINE_TOTAL')

    def test_footer_disagrees(self):
        self.case['documents'][0]['reported_direct_total']['value'] = '4649.99'
        self.blocked('E_ESTIMATE_TOTAL')

    def test_duplicate_work(self):
        self.case['lines'][3]['work_components'] = ['shingle-install']
        self.blocked('E_DUPLICATE_WORK')

    def test_quote_includes_separately_billed_work(self):
        self.case['lines'][1]['quote_inclusions'] = ['flashing-replace']
        self.blocked('E_DUPLICATE_WORK')

    def test_line_reused_in_two_groups(self):
        self.case['groups'][1]['proposed'].append('P1')
        self.blocked('E_LINE_REUSED')

    def test_unmapped_line_preserved(self):
        self.case['groups'].pop()
        r = self.run_case()
        self.assertEqual('blocked', r['status'])
        self.assertEqual(['B4', 'P4a', 'P4b'], r['unmapped_lines'])

    def test_one_to_many_group(self):
        r = self.run_case()
        self.assertEqual('draft', r['status'])
        self.assertEqual('0.00', r['groups'][3]['delta'])
        self.assertEqual(['P4a', 'P4b'], r['groups'][3]['proposed'])

    def test_many_to_one_group(self):
        for line in self.case['lines']:
            line['side'] = 'proposed' if line['side'] == 'baseline' else 'baseline'
        for d in self.case['documents'][:2]:
            d['role'] = 'proposed' if d['role'] == 'baseline' else 'baseline'
        for g in self.case['groups']:
            g['baseline'], g['proposed'] = g['proposed'], g['baseline']
        r = self.run_case()
        self.assertEqual('draft', r['status'])
        self.assertEqual('-640.00', r['totals']['delta_direct'])

    def test_unknown_coverage_stays_unknown(self):
        r = self.run_case()
        self.assertEqual('draft', r['status'])
        self.assertEqual('unknown', r['groups'][0]['coverage_status'])
        self.assertIsNone(r['financial_bridge']['RCV'])

    def test_unsupported_coverage_blocked(self):
        self.case['groups'][0]['coverage'] = {'status': 'confirmed', 'source_ids': [], 'reviewer': None}
        self.blocked('E_COVERAGE')

    def test_insufficient_scope_evidence(self):
        self.case['groups'][0]['scope_support']['status'] = 'insufficient'
        self.blocked('E_SCOPE')

    def test_unknown_evidence_id(self):
        self.case['groups'][0]['source_ids'].append('EX-NOT-REAL')
        self.blocked('E_SOURCE_REF')

    def test_missing_counterargument(self):
        self.case['groups'][0]['counterargument'] = ''
        self.blocked('E_ARGUMENT')

    def test_missing_mapping_rationale(self):
        self.case['groups'][3]['mapping_rationale'] = ''
        self.blocked('E_MAPPING')

    def test_plan_area_not_roof_surface(self):
        self.case['lines'][1]['area_basis'] = 'plan'
        self.blocked('E_AREA_BASIS')

    def test_double_slope(self):
        self.case['lines'][1]['geometry']['apply_slope'] = True
        self.blocked('E_DOUBLE_SLOPE')

    def test_double_waste(self):
        self.case['lines'][1]['geometry']['waste_included'] = True
        self.case['lines'][1]['geometry']['apply_waste'] = True
        self.blocked('E_DOUBLE_WASTE')

    def test_financial_basis_mismatch(self):
        self.case['lines'][1]['financial_basis'] = 'RCV'
        self.blocked('E_BASIS')

    def test_nonfinite_float_exponent_and_boolean_rejected(self):
        for value in ['NaN', 'Infinity', '1e3', 12.0, True, '-1']:
            with self.subTest(value=value):
                self.field(1, 'quantity', value)
                self.blocked('E_DECIMAL')

    def test_half_up_line_rounding(self):
        self.field(4, 'quantity', '1'); self.field(4, 'unit_price', '450.005'); self.field(4, 'reported_total', '450.01')
        self.field(5, 'unit_price', '450.005'); self.field(5, 'reported_total', '450.01')
        self.retotal()
        r = self.run_case()
        self.assertEqual('draft', r['status'])
        self.assertEqual('4650.01', r['totals']['baseline_direct'])

    def test_source_hash_mismatch(self):
        self.case['documents'][0]['sha256'] = '0' * 64
        self.blocked('E_SOURCE_HASH')

    def test_source_traversal_refused(self):
        self.case['documents'][0]['path'] = '../secret.txt'
        self.blocked('E_SOURCE_PATH')

    def test_reference_page_out_of_range(self):
        self.case['lines'][1]['quantity']['source']['page'] = 9
        self.blocked('E_SOURCE_REF')

    def test_reference_crop_outside_image(self):
        self.case['lines'][1]['quantity']['source']['bbox'] = [0, 0, 99999, 99999]
        self.blocked('E_COORDINATES')

    def test_synthetic_only(self):
        self.case['synthetic'] = False
        self.blocked('E_REAL_DATA')

    def test_missing_required_structure(self):
        del self.case['lines'][1]['quantity']
        self.blocked('E_SCHEMA')

    def test_unknown_schema_version(self):
        self.case['schema_version'] = 'future/99'
        self.blocked('E_SCHEMA')

    def test_input_is_not_mutated(self):
        before = copy.deepcopy(self.case)
        r = self.run_case()
        self.assertEqual('draft', r['status'])
        self.assertEqual(before, self.case)


if __name__ == '__main__':
    unittest.main()
