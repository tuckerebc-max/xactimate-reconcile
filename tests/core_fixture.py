from __future__ import annotations

import hashlib
from pathlib import Path


def make_case(tmp_path: Path) -> tuple[dict, Path]:
    source_root = tmp_path / "sources"
    source_root.mkdir(parents=True)
    originals = source_root / "originals"
    originals.mkdir()

    payloads = {
        "baseline.txt": b"synthetic baseline estimate\n",
        "proposed.txt": b"synthetic proposed estimate\n",
        "evidence.txt": b"synthetic roof inspection\n",
        "policy.txt": b"synthetic policy excerpt\n",
    }
    for name, payload in payloads.items():
        (originals / name).write_bytes(payload)

    def sha(name: str) -> str:
        return hashlib.sha256(payloads[name]).hexdigest()

    def source(doc_id: str) -> dict:
        return {
            "doc_id": doc_id,
            "page": 1,
            "bbox": [10, 10, 90, 30],
            "coordinate_space": "pixels",
            "image_size": [100, 100],
            "method": "manual_synthetic",
        }

    def number(value: str | None, doc_id: str) -> dict:
        return {
            "value": value,
            "raw_text": value,
            "alternatives": [],
            "resolution": None,
            "verification": "synthetic_checked",
            "reviewer": "fixture_author",
            "reviewed_at": "2026-09-21T12:00:00Z",
            "source": source(doc_id),
            "ocr_confidence": None,
        }

    def document(doc_id: str, role: str, name: str, total: str | None) -> dict:
        return {
            "id": doc_id,
            "role": role,
            "path": f"originals/{name}",
            "sha256": sha(name),
            "page_count": 1,
            "received_pages": [1],
            "pages": [{"page": 1, "width": 100, "height": 100}],
            "version": "v1",
            "date": "2026-09-20",
            "kind": "synthetic_source",
            "estimate_complete": role in {"baseline", "proposed"},
            "synthetic": True,
            "reported_direct_total": number(total, doc_id) if total is not None else None,
        }

    def line(line_id: str, side: str, doc_id: str, quantity: str, price: str, total: str) -> dict:
        return {
            "id": line_id,
            "side": side,
            "kind": "work",
            "description": "Synthetic shingle work",
            "specification": "laminated shingle",
            "roof_location": "main-roof",
            "quantity": number(quantity, doc_id),
            "unit": "SQ",
            "unit_price": number(price, doc_id),
            "reported_total": number(total, doc_id),
            "financial_basis": "direct_pre_tax",
            "area_basis": "roof_surface",
            "geometry": {
                "slope_included": True,
                "waste_included": False,
                "apply_slope": False,
                "apply_waste": False,
            },
            "work_components": ["shingle-install"],
            "quote_inclusions": [],
            "source": source(doc_id),
        }

    case = {
        "schema_version": "xr-case/1.0",
        "synthetic": True,
        "case_id": "SYN-CORE-1",
        "title": "Synthetic core fixture",
        "roof_type": "shingle",
        "as_of": "2026-09-21",
        "jurisdiction": {"country": "US", "state": "AZ", "municipality": "Phoenix", "verified": True},
        "sender": {
            "name": "Fixture Author",
            "role": "estimator",
            "authority_status": "synthetic",
            "authority_evidence_ids": [],
        },
        "currency": "USD",
        "rounding": "ROUND_HALF_UP",
        "financial_basis": "direct_pre_tax",
        "baseline_label": "Synthetic baseline",
        "proposed_label": "Synthetic proposed",
        "author_role": "synthetic fixture",
        "price_context": {"list": None, "month": None, "location": "Phoenix synthetic"},
        "documents": [
            document("DOC-B", "baseline", "baseline.txt", "100.00"),
            document("DOC-P", "proposed", "proposed.txt", "132.00"),
            document("DOC-E", "evidence", "evidence.txt", None),
            document("DOC-PL", "policy", "policy.txt", None),
        ],
        "evidence": [
            {"id": "EV-ROOF", "doc_id": "DOC-E", "page": 1, "description": "Synthetic roof observation"},
            {"id": "EV-POLICY", "doc_id": "DOC-PL", "page": 1, "description": "Synthetic policy evidence"},
        ],
        "lines": [
            line("B-1", "baseline", "DOC-B", "10", "10", "100.00"),
            line("P-1", "proposed", "DOC-P", "12", "11", "132.00"),
        ],
        "groups": [{
            "claim_id": "C-001",
            "title": "Shingle quantity and price",
            "baseline": ["B-1"],
            "proposed": ["P-1"],
            "roof_location": "main-roof",
            "change_type": "quantity_price",
            "mapping_rationale": "Same specification and work component.",
            "source_ids": ["EV-ROOF"],
            "scope_support": {"status": "supported", "source_ids": ["EV-ROOF"]},
            "coverage": {"status": "unknown", "source_ids": [], "reviewer": None},
            "counterargument": "Measurement should be independently reviewed.",
            "disposition": "candidate_change",
            "absence_verified": False,
        }],
        "financial_adjustments": {"baseline": [], "proposed": []},
        "payment_scenario": None,
        "notes": "Synthetic data only.",
    }
    return case, source_root
