from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import tempfile
import unittest

import bootstrap  # noqa: F401
from xactimate_reconcile.extensions import select_packs, validate_pack


def make_pack(tmp_path):
    asset = tmp_path / "example.txt"
    asset.write_bytes(b"synthetic example\n")
    return {
        "schema_version": "xr-extension/1.0", "id": "az-roof-context", "version": "1.0",
        "type": "geography", "title": "Arizona roof context",
        "jurisdiction": {"country": "US", "state": "AZ", "municipality": None},
        "roof_types": ["shingle"], "effective_from": "2026-01-01", "effective_to": "2026-12-31",
        "review": {"status": "reviewed", "reviewer": "Reviewer", "reviewed_at": "2026-01-02"},
        "sources": [{"id": "SRC-1", "title": "Synthetic source", "url_or_document": "local",
                     "accessed_date": "2026-01-01", "limitation": "Synthetic only"}],
        "entries": [{"id": "ENTRY-1", "title": "Example", "kind": "writing_example",
                     "content": "A writing example cannot authorize payment.", "source_ids": ["SRC-1"],
                     "amount": None, "unit": None, "currency": None, "observed_at": None,
                     "expires_at": None, "artifact_path": "example.txt",
                     "artifact_sha256": hashlib.sha256(b"synthetic example\n").hexdigest()}],
    }


class ExtensionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_validate_pack_checks_asset_and_selection_returns_original_pack(self):
        pack = make_pack(self.tmp_path)
        self.assertEqual(validate_pack(pack, self.tmp_path), [])
        case = {"as_of": "2026-09-21", "roof_type": "shingle",
                "jurisdiction": {"country": "US", "state": "AZ", "municipality": "Phoenix", "verified": True}}
        selected = select_packs([pack], case)
        self.assertIs(selected["applicable"][0]["pack"], pack)
        self.assertEqual(selected["excluded"], [])

    def test_selection_excludes_draft_future_expired_and_mismatched_packs(self):
        base = make_pack(self.tmp_path)
        packs = []
        for ident, edit in [
            ("draft", lambda p: p["review"].update(status="draft")),
            ("future", lambda p: p.update(effective_from="2027-01-01", effective_to=None)),
            ("expired", lambda p: p.update(effective_to="2026-01-31")),
            ("roof", lambda p: p.update(roof_types=["tile"])),
            ("state", lambda p: p["jurisdiction"].update(state="NV")),
        ]:
            item = copy.deepcopy(base)
            item["id"] = ident
            edit(item)
            packs.append(item)
        case = {"as_of": "2026-09-21", "roof_type": "shingle",
                "jurisdiction": {"country": "US", "state": "AZ", "municipality": "Phoenix", "verified": True}}
        result = select_packs(packs, case)
        self.assertEqual(result["applicable"], [])
        self.assertEqual({x["id"] for x in result["excluded"]}, {"draft", "future", "expired", "roof", "state"})

    def test_unknown_municipality_warns_and_excludes_city_pack(self):
        pack = make_pack(self.tmp_path)
        pack["jurisdiction"]["municipality"] = "Phoenix"
        case = {"as_of": "2026-09-21", "roof_type": "shingle",
                "jurisdiction": {"country": "US", "state": "AZ", "municipality": None, "verified": False}}
        result = select_packs([pack], case)
        self.assertEqual(result["applicable"], [])
        self.assertTrue(any("municipality" in warning.lower() for warning in result["warnings"]))

    def test_exemplar_hash_mismatch_and_path_escape_are_invalid(self):
        pack = make_pack(self.tmp_path)
        pack["entries"][0]["artifact_sha256"] = "0" * 64
        self.assertTrue(any("hash" in error.lower() for error in validate_pack(pack, self.tmp_path)))
        pack["entries"][0]["artifact_path"] = "../outside.txt"
        self.assertTrue(any("escape" in error.lower() for error in validate_pack(pack, self.tmp_path)))

    def test_lexical_asset_escape_is_invalid_even_without_pack_root(self):
        pack = make_pack(self.tmp_path)
        pack["entries"][0]["artifact_path"] = "../outside.txt"
        self.assertTrue(any("relative" in error.lower() or "escape" in error.lower()
                            for error in validate_pack(pack)))

    def test_wrong_nested_json_types_return_errors_instead_of_raising(self):
        pack = make_pack(self.tmp_path)
        pack["roof_types"] = [[]]
        pack["entries"][0]["source_ids"] = [{}]
        errors = validate_pack(pack)
        self.assertTrue(errors)

    def test_expired_entry_is_filtered_regardless_of_kind(self):
        pack = make_pack(self.tmp_path)
        pack["entries"][0]["kind"] = "technical_note"
        pack["entries"][0]["expires_at"] = "2026-02-01"
        case = {"as_of": "2026-09-21", "roof_type": "shingle",
                "jurisdiction": {"country": "US", "state": "AZ", "municipality": "Phoenix", "verified": True}}
        result = select_packs([pack], case)
        self.assertEqual(result["applicable"][0]["entries"], [])
        self.assertTrue(any("stale" in warning.lower() for warning in result["warnings"]))


if __name__ == "__main__":
    unittest.main()
