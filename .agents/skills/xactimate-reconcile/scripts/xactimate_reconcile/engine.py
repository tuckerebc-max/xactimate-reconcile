"""Deterministic, standard-library reconciliation engine.

The engine calculates a reviewable draft.  It never authorizes release, infers
coverage, selects a price, or submits a claim.
"""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, localcontext
import hashlib
from pathlib import Path
import re
from typing import Any

from .contracts import digest, money

REPORT_VERSION = "xr-report/1.0"
CASE_VERSION = "xr-case/1.0"
MAX_SOURCE_BYTES = 100 * 1024 * 1024
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}$")
DECIMAL_RE = re.compile(r"^-?(?:0|[1-9][0-9]{0,17})(?:\.[0-9]{1,8})?$")
CATEGORY_RE = re.compile(r"^(?:A-O|B-I)[0-9]{2}$")
UNITS = {
    "SF": ("area", Decimal("1")),
    "SQ": ("area", Decimal("100")),
    "LF": ("length", Decimal("1")),
    "EA": ("count", Decimal("1")),
}


def _safe_id(value: Any) -> bool:
    return isinstance(value, str) and ID_RE.fullmatch(value) is not None


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _iso_date(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


def _iso_datetime(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def _document_fingerprint_context(doc: Any, page: Any) -> dict[str, Any] | None:
    if not isinstance(doc, dict):
        return None
    pages = doc.get("pages") if isinstance(doc.get("pages"), list) else []
    page_metadata = None
    if isinstance(page, int) and 1 <= page <= len(pages):
        page_metadata = pages[page - 1]
    return {
        "id": doc.get("id"),
        "sha256": doc.get("sha256"),
        "version": doc.get("version"),
        "role": doc.get("role"),
        "page": page,
        "page_metadata": page_metadata,
    }


def review_subjects(case: dict) -> dict[str, dict]:
    """Build deterministic numeric review subjects and edit-sensitive fingerprints."""
    if not isinstance(case, dict):
        return {}
    documents = {
        item.get("id"): item for item in case.get("documents", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    currency = case.get("currency")
    subjects: dict[str, dict] = {}

    def add(key: str, field: Any, unit: Any, context: dict[str, Any]) -> None:
        if not isinstance(field, dict):
            return
        source = field.get("source") if isinstance(field.get("source"), dict) else None
        doc = documents.get(source.get("doc_id")) if source else None
        page = source.get("page") if source else None
        fingerprint_value = {
            "numeric_field": field,
            "context": context,
            "document": _document_fingerprint_context(doc, page),
        }
        subjects[key] = {
            "fingerprint": digest(fingerprint_value),
            "value": field.get("value"),
            "unit": unit,
            "source": source,
            "raw_text": field.get("raw_text"),
        }

    for line in case.get("lines", []):
        if not isinstance(line, dict) or not isinstance(line.get("id"), str):
            continue
        context = {name: line.get(name) for name in
                   ("id", "side", "kind", "unit", "specification", "roof_location", "geometry")}
        add(f"line:{line['id']}:quantity", line.get("quantity"), line.get("unit"), context)
        add(f"line:{line['id']}:unit_price", line.get("unit_price"),
            f"{currency}/{line.get('unit')}" if currency and line.get("unit") else currency, context)
        add(f"line:{line['id']}:reported_total", line.get("reported_total"), currency, context)
    for doc in case.get("documents", []):
        if isinstance(doc, dict) and isinstance(doc.get("id"), str):
            context = {name: doc.get(name) for name in ("id", "role", "version", "date", "kind")}
            add(f"document:{doc['id']}:reported_direct_total", doc.get("reported_direct_total"), currency, context)
    adjustments = case.get("financial_adjustments")
    if isinstance(adjustments, dict):
        for side in ("baseline", "proposed"):
            for item in adjustments.get(side, []) if isinstance(adjustments.get(side), list) else []:
                if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                    continue
                context = {"side": side, **{name: item.get(name) for name in
                           ("id", "label", "kind", "method", "basis", "evidence_ids")}}
                add(f"adjustment:{side}:{item['id']}:amount", item.get("amount"), currency, context)
                add(f"adjustment:{side}:{item['id']}:rate", item.get("rate"), "fraction", context)
    payment = case.get("payment_scenario")
    if isinstance(payment, dict):
        base_context = {name: payment.get(name) for name in ("label", "evidence_ids", "policy_evidence_ids")}
        add("payment:start", payment.get("start"), currency, base_context)
        for step in payment.get("steps", []) if isinstance(payment.get("steps"), list) else []:
            if isinstance(step, dict) and isinstance(step.get("id"), str):
                add(f"payment:{step['id']}:amount", step.get("amount"), currency,
                    {**base_context, **{name: step.get(name) for name in
                     ("id", "label", "operation", "evidence_ids")}})
    return subjects


def _review_summary(case: dict, reviews: Any, subjects: dict[str, dict], issue) -> dict[str, list[str]]:
    latest: dict[str, dict] = {}
    if reviews is None:
        reviews = []
    if not isinstance(reviews, list):
        issue("E_REVIEW", "reviews", "Reviews must be an array.")
        reviews = []
    for index, review in enumerate(reviews):
        ref = f"reviews[{index}]"
        if not isinstance(review, dict):
            issue("E_REVIEW", ref, "Review entry must be an object.")
            continue
        required = {"subject", "fingerprint", "decision", "kind", "reviewer", "reviewed_at"}
        if not required.issubset(review):
            issue("E_REVIEW", ref, "Review entry is missing required fields.")
            continue
        if (review.get("decision") not in {"confirm", "reject"}
                or review.get("kind") not in {"human", "ai", "synthetic"}
                or not _nonempty(review.get("reviewer"))
                or not _iso_datetime(review.get("reviewed_at"))):
            issue("E_REVIEW", ref, "Review decision, kind, reviewer, or timestamp is invalid.")
            continue
        subject = review.get("subject")
        if not isinstance(subject, str) or subject not in subjects:
            issue("R_REVIEW_SUBJECT", str(subject), "Review names an unknown subject.", "review")
            continue
        latest[subject] = review

    summary = {
        "required": sorted(subjects),
        "human_confirmed": [],
        "ai_confirmed": [],
        "synthetic_confirmed": [],
        "pending_subjects": [],
        "stale_subjects": [],
    }
    for subject, descriptor in subjects.items():
        review = latest.get(subject)
        if review is None:
            summary["pending_subjects"].append(subject)
        elif review.get("fingerprint") != descriptor["fingerprint"]:
            summary["stale_subjects"].append(subject)
            summary["pending_subjects"].append(subject)
        elif review.get("decision") != "confirm":
            summary["pending_subjects"].append(subject)
        else:
            summary[f"{review['kind']}_confirmed"].append(subject)
    for values in summary.values():
        values.sort()
    return summary


def _base_report(case: Any) -> dict[str, Any]:
    return {
        "schema_version": REPORT_VERSION,
        "case_id": case.get("case_id") if isinstance(case, dict) else None,
        "synthetic": bool(case.get("synthetic")) if isinstance(case, dict) else False,
        "status": "blocked",
        "release_allowed": False,
        "issues": [],
        "groups": [],
        "totals": None,
        "partial_totals": {"supported_delta": None, "is_complete": False},
        "unmapped_lines": [],
        "financial_bridge": {"baseline": None, "proposed": None, "payment_scenario": None,
                             "net_payable": None},
        "source_checks": [],
        "review_summary": {"required": [], "human_confirmed": [], "ai_confirmed": [],
                           "synthetic_confirmed": [], "pending_subjects": [], "stale_subjects": []},
        "limitations": [
            "Draft calculation only; release is never authorized by this engine.",
            "Coverage and payment entitlement are not inferred.",
            "Price context is recorded but never used to select a price.",
            "Review receipts are assertions and do not authenticate identity.",
        ],
    }


def reconcile(case: dict, source_root: Path, reviews: list | None = None) -> dict:
    """Validate and reconcile one case, always returning a JSON-serializable report."""
    report = _base_report(case)
    blocked = False

    def issue(code: str, ref: str, message: str, severity: str = "error") -> None:
        nonlocal blocked
        report["issues"].append({"code": code, "ref": ref, "message": message, "severity": severity})
        if severity == "error":
            blocked = True

    try:
        if not isinstance(case, dict):
            issue("E_SCHEMA", "case", "Case must be an object.")
            return report
        required_root = {"schema_version", "synthetic", "case_id", "currency", "rounding",
                         "financial_basis", "documents", "evidence", "lines", "groups"}
        allowed_root = required_root | {
            "title", "roof_type", "as_of", "jurisdiction", "sender", "baseline_label",
            "proposed_label", "author_role", "price_context", "financial_adjustments",
            "payment_scenario", "notes",
        }
        missing = sorted(required_root - case.keys())
        if missing:
            issue("E_SCHEMA", "case", "Missing root fields: " + ", ".join(missing))
            return report
        unexpected = sorted(case.keys() - allowed_root)
        if unexpected:
            issue("E_SCHEMA", "case", "Unexpected root fields: " + ", ".join(unexpected))
        if case.get("schema_version") != CASE_VERSION:
            issue("E_SCHEMA", "case.schema_version", f"Expected {CASE_VERSION}.")
        if type(case.get("synthetic")) is not bool:
            issue("E_SCHEMA", "case.synthetic", "synthetic must be a boolean.")
        if not _safe_id(case.get("case_id")):
            issue("E_ID", "case.case_id", "case_id must be a safe identifier without surrounding whitespace.")
        if case.get("currency") != "USD":
            issue("E_BASIS", "case.currency", "Only explicit USD arithmetic is supported.")
        if case.get("rounding") != "ROUND_HALF_UP":
            issue("E_ROUNDING", "case.rounding", "ROUND_HALF_UP must be explicit.")
        if case.get("financial_basis") != "direct_pre_tax":
            issue("E_BASIS", "case.financial_basis", "direct_pre_tax must be explicit.")
        if "roof_type" in case and case["roof_type"] not in {"shingle", "tile", "low_slope"}:
            issue("E_SCHEMA", "case.roof_type", "Unsupported roof type.")
        if "as_of" in case and not _iso_date(case["as_of"]):
            issue("E_DATE", "case.as_of", "as_of must be an ISO date.")
        for name in ("documents", "evidence", "lines", "groups"):
            if not isinstance(case.get(name), list):
                issue("E_SCHEMA", f"case.{name}", f"{name} must be an array.")
        if blocked:
            return report

        def index(items: list, key: str, label: str) -> dict[str, dict]:
            result: dict[str, dict] = {}
            for pos, item in enumerate(items):
                ref = f"{label}[{pos}]"
                if not isinstance(item, dict):
                    issue("E_SCHEMA", ref, "Entry must be an object.")
                    continue
                ident = item.get(key)
                if not _safe_id(ident):
                    issue("E_ID", ref, f"{key} must be a safe identifier without surrounding whitespace.")
                    continue
                if ident in result:
                    issue("E_DUPLICATE_ID", ident, "Identifiers must be unique within their collection.")
                else:
                    result[ident] = item
            return result

        docs = index(case["documents"], "id", "documents")
        evidence = index(case["evidence"], "id", "evidence")
        lines = index(case["lines"], "id", "lines")
        groups = index(case["groups"], "claim_id", "groups")

        subjects = review_subjects(case)
        report["review_summary"] = _review_summary(case, reviews, subjects, issue)

        root: Path | None = None
        try:
            if source_root is None:
                raise ValueError("missing")
            root = Path(source_root).resolve(strict=True)
            if not root.is_dir():
                raise ValueError("not a directory")
        except (OSError, TypeError, ValueError):
            issue("E_SOURCE_ROOT", "case", "A readable source directory is required.")

        active_by_side: dict[str, list[dict]] = {"baseline": [], "proposed": []}
        for did, doc in docs.items():
            role = doc.get("role")
            if role not in {"baseline", "proposed", "evidence", "policy", "operator"}:
                issue("E_SCHEMA", did, "Unknown document role.")
                continue
            if role in active_by_side:
                active_by_side[role].append(doc)
            if not _nonempty(doc.get("version")) or not _nonempty(doc.get("date")):
                issue("E_SCHEMA", did, "Document version and date must be nonempty.")
            elif not _iso_date(doc["date"]):
                issue("E_DATE", did, "Document date must be ISO format.")
            page_count = doc.get("page_count")
            pages = doc.get("received_pages")
            valid_page_count = type(page_count) is int and 1 <= page_count <= 10000
            if not valid_page_count:
                issue("E_SCHEMA", did, "page_count must be an integer from 1 to 10000.")
            if not isinstance(pages, list) or any(type(p) is not int for p in pages):
                issue("E_SCHEMA", did, "received_pages must contain integer page numbers.")
                pages = []
            if role in active_by_side and (not valid_page_count
                                            or pages != list(range(1, page_count + 1))
                                            or doc.get("estimate_complete") is not True):
                issue("E_INCOMPLETE", did, "Active estimate pages are missing, reordered, or incomplete.")
            sha = doc.get("sha256")
            if not isinstance(sha, str) or re.fullmatch(r"[0-9a-f]{64}", sha) is None:
                issue("E_SOURCE_HASH", did, "Document SHA-256 must be 64 lowercase hexadecimal characters.")
            if root is not None and isinstance(sha, str):
                try:
                    rel = Path(doc.get("path"))
                    if rel.is_absolute():
                        raise ValueError("absolute")
                    source = (root / rel).resolve(strict=True)
                    if not source.is_relative_to(root) or not source.is_file():
                        raise ValueError("escape")
                    if source.stat().st_size > MAX_SOURCE_BYTES:
                        raise ValueError("oversized")
                    hasher = hashlib.sha256()
                    with source.open("rb") as stream:
                        while chunk := stream.read(1024 * 1024):
                            hasher.update(chunk)
                    actual = hasher.hexdigest()
                    match = actual == sha
                    report["source_checks"].append({"doc_id": did, "sha256": actual, "match": match})
                    if not match:
                        issue("E_SOURCE_HASH", did, "Original bytes differ from the recorded hash.")
                except (OSError, TypeError, ValueError):
                    issue("E_SOURCE_PATH", did, "Source path is missing, unreadable, oversized, or escapes source_root.")
        for side, selected in active_by_side.items():
            if len(selected) != 1:
                issue("E_ESTIMATE_VERSION", side, "Exactly one active estimate document is required for each side.")

        def check_source(source: Any, ref: str, expected_side: str | None = None) -> bool:
            ok = True
            if not isinstance(source, dict):
                issue("E_SOURCE_REF", ref, "A source locator object is required.")
                return False
            required = {"doc_id", "page", "bbox", "coordinate_space", "image_size", "method"}
            if not required.issubset(source):
                issue("E_SOURCE_REF", ref, "Source locator is missing required fields.")
                return False
            doc = docs.get(source.get("doc_id"))
            page = source.get("page")
            if doc is None or type(page) is not int or page not in doc.get("received_pages", []):
                issue("E_SOURCE_REF", ref, "Source names an unknown document or page.")
                ok = False
            elif expected_side is not None and doc.get("role") != expected_side:
                issue("E_SOURCE_SIDE", ref, "Line numeric source must come from its estimate side.")
                ok = False
            bbox, image_size = source.get("bbox"), source.get("image_size")
            numeric = lambda x: type(x) in (int, float) and abs(x) < 1e9
            if (source.get("coordinate_space") != "pixels" or not isinstance(bbox, list) or len(bbox) != 4
                    or not isinstance(image_size, list) or len(image_size) != 2
                    or not all(numeric(v) for v in bbox + image_size)
                    or not (0 <= bbox[0] < bbox[2] <= image_size[0]
                            and 0 <= bbox[1] < bbox[3] <= image_size[1])):
                issue("E_COORDINATES", ref, "A bounded pixel crop and image dimensions are required.")
                ok = False
            elif (doc is not None and type(page) is int and isinstance(doc.get("pages"), list)
                  and 1 <= page <= len(doc["pages"])):
                meta = doc["pages"][page - 1]
                if isinstance(meta, dict):
                    width, height = meta.get("width"), meta.get("height")
                    if (type(width) in (int, float) and type(height) in (int, float)
                            and (image_size != [width, height]
                                 or bbox[2] > width or bbox[3] > height)):
                        issue("E_COORDINATES", ref, "Source coordinates disagree with recorded page dimensions.")
                        ok = False
            if source.get("method") not in {"manual_synthetic", "native_text", "local_ocr", "vision", "manual"}:
                issue("E_SCHEMA", ref, "Unknown extraction method.")
                ok = False
            return ok

        numeric_values: dict[str, Decimal | None] = {}

        def number(field: Any, ref: str, *, expected_side: str | None = None,
                   nonnegative: bool = False, signed: bool = False) -> Decimal | None:
            if not isinstance(field, dict):
                issue("E_SCHEMA", ref, "Numeric field must be an object.")
                numeric_values[ref] = None
                return None
            required = {"value", "raw_text", "alternatives", "resolution", "verification",
                        "reviewer", "reviewed_at", "source"}
            if not required.issubset(field):
                issue("E_SCHEMA", ref, "Numeric field is missing required fields.")
                numeric_values[ref] = None
                return None
            source_ok = check_source(field.get("source"), ref, expected_side)
            if field.get("verification") not in {"unreviewed", "ambiguous", "ai_checked", "synthetic_checked"}:
                issue("E_SCHEMA", ref, "Unknown numeric verification value.")
            alternatives = field.get("alternatives")
            if not isinstance(alternatives, list) or any(not isinstance(v, str) for v in alternatives):
                issue("E_SCHEMA", ref, "Numeric alternatives must be strings.")
            ambiguous = field.get("verification") == "ambiguous" or bool(alternatives and not _nonempty(field.get("resolution")))
            raw = field.get("value")
            if raw is None or ambiguous:
                issue("R_NUMERIC_UNKNOWN", ref, "Missing or ambiguous number is held and never zero-filled.", "review")
                numeric_values[ref] = None
                return None
            if not source_ok:
                numeric_values[ref] = None
                return None
            if not isinstance(raw, str) or DECIMAL_RE.fullmatch(raw) is None:
                issue("E_DECIMAL", ref, "Value must be a bounded plain decimal string or null.")
                numeric_values[ref] = None
                return None
            try:
                value = Decimal(raw)
            except InvalidOperation:
                issue("E_DECIMAL", ref, "Value is not a finite decimal.")
                numeric_values[ref] = None
                return None
            if not value.is_finite() or (nonnegative and value < 0) or (not signed and value < 0):
                issue("E_DECIMAL", ref, "Value has an invalid sign or is nonfinite.")
                numeric_values[ref] = None
                return None
            numeric_values[ref] = value
            return value

        for eid, item in evidence.items():
            doc = docs.get(item.get("doc_id"))
            if doc is None or type(item.get("page")) is not int or item["page"] not in doc.get("received_pages", []):
                issue("E_SOURCE_REF", eid, "Evidence names an unknown document or page.")
            if not _nonempty(item.get("description")):
                issue("E_SCHEMA", eid, "Evidence description must be nonempty.")

        parsed: dict[str, dict[str, Any]] = {}
        work_seen: dict[tuple[str, str, str], str] = {}
        held_lines: dict[str, list[str]] = {}
        for lid, line in lines.items():
            held_lines[lid] = []
            side = line.get("side")
            if side not in {"baseline", "proposed"}:
                issue("E_SCHEMA", lid, "Line side must be baseline or proposed.")
                continue
            for name in ("description", "specification"):
                if not _nonempty(line.get(name)):
                    issue("E_SCHEMA", lid, f"{name} must be nonempty text.")
            if not _safe_id(line.get("roof_location")):
                issue("E_ID", lid, "roof_location must be a safe identifier.")
            if line.get("financial_basis") != case.get("financial_basis"):
                issue("E_BASIS", lid, "Line and case financial bases differ.")
            if not check_source(line.get("source"), lid, side):
                held_lines[lid].append("line_source_invalid")
            unit = line.get("unit")
            if unit not in UNITS:
                issue("E_UNIT", lid, "Unsupported unit.")
                continue
            area = line.get("area_basis")
            if ((unit in {"SF", "SQ"} and area not in {"roof_surface", "plan"})
                    or (unit not in {"SF", "SQ"} and area != "not_area")):
                issue("E_AREA_BASIS", lid, "Unit and area basis are inconsistent.")
            geometry = line.get("geometry")
            flags = ("slope_included", "waste_included", "apply_slope", "apply_waste")
            if not isinstance(geometry, dict) or any(type(geometry.get(name)) is not bool for name in flags):
                issue("E_SCHEMA", lid, "Geometry must contain four boolean flags.")
            else:
                for adjustment in ("slope", "waste"):
                    if geometry[f"apply_{adjustment}"]:
                        held_lines[lid].append(f"geometry_{adjustment}_requires_manual_review")
                        issue("R_GEOMETRY", lid, "Requested geometry transform requires a reviewed manual step.", "review")
            kind = line.get("kind", "work")
            if kind not in {"work", "credit"}:
                issue("E_SCHEMA", lid, "Line kind must be work or credit.")
            q = number(line.get("quantity"), f"line:{lid}:quantity", expected_side=side, nonnegative=True)
            p = number(line.get("unit_price"), f"line:{lid}:unit_price", expected_side=side, nonnegative=True)
            t = number(line.get("reported_total"), f"line:{lid}:reported_total", expected_side=side,
                       signed=kind == "credit")
            if None in (q, p, t):
                held_lines[lid].append("numeric_value_missing_or_ambiguous")
            else:
                expected = Decimal(money(q * p))
                if kind == "credit":
                    expected = -expected
                line_total_ok = t == expected and t == t.quantize(Decimal("0.01"))
                if not line_total_ok:
                    issue("E_LINE_TOTAL", lid, "Reported total differs from quantity times unit price at cent precision.")
                    held_lines[lid].append("line_total_invalid")
                dimension, factor = UNITS[unit]
                if line_total_ok:
                    signed_price = -p if kind == "credit" else p
                    parsed[lid] = {"quantity": q * factor, "unit_price": signed_price / factor,
                                   "total": t, "dimension": dimension}
            components = line.get("work_components")
            inclusions = line.get("quote_inclusions")
            if (not isinstance(components, list) or not components
                    or not isinstance(inclusions, list)
                    or any(not _safe_id(v) for v in components + inclusions)):
                issue("E_SCHEMA", lid, "Work components must be safe IDs and the primary list cannot be empty.")
            else:
                for component in set(components + inclusions):
                    key = (side, line.get("roof_location"), component)
                    if key in work_seen:
                        issue("E_DUPLICATE_WORK", lid, f"Work also appears in {work_seen[key]}: {component}")
                    else:
                        work_seen[key] = lid

        footer_values: dict[str, Decimal | None] = {}
        for side, selected in active_by_side.items():
            if len(selected) != 1:
                continue
            doc = selected[0]
            footer = number(doc.get("reported_direct_total"),
                            f"document:{doc['id']}:reported_direct_total", expected_side=side, signed=True)
            footer_values[side] = footer
            side_lines = [lid for lid, line in lines.items() if line.get("side") == side]
            if footer is not None and all(lid in parsed for lid in side_lines):
                actual = sum((parsed[lid]["total"] for lid in side_lines), Decimal(0))
                if footer != actual:
                    issue("E_ESTIMATE_TOTAL", doc["id"], "Footer differs from supplied line totals.")

        used: Counter[str] = Counter()
        group_data: list[tuple[dict, dict]] = []
        for cid, group in groups.items():
            baseline = group.get("baseline")
            proposed = group.get("proposed")
            reasons: list[str] = []
            if not isinstance(baseline, list) or not isinstance(proposed, list):
                issue("E_MAPPING", cid, "Group sides must be arrays.")
                continue
            if not baseline and not proposed:
                issue("E_MAPPING", cid, "A group cannot be empty.")
            if len(baseline) > 1 and len(proposed) > 1:
                issue("E_MAPPING_TOPOLOGY", cid, "Many-to-many mapping requires explicit allocation.")
            if not _safe_id(group.get("roof_location")):
                issue("E_ID", cid, "Group roof_location must be a safe identifier.")
            if not _nonempty(group.get("mapping_rationale")):
                issue("E_MAPPING", cid, "Mapping rationale must be nonempty.")
            if not _nonempty(group.get("counterargument")):
                issue("E_ARGUMENT", cid, "Counterargument must be nonempty.")
            change_type = group.get("change_type")
            if change_type not in {"quantity_price", "bundle", "scope", "specification_bundle"}:
                issue("E_SCHEMA", cid, "Unknown change type.")
            if not baseline or not proposed:
                opposite = "proposed" if not proposed else "baseline"
                complete = len(active_by_side[opposite]) == 1 and active_by_side[opposite][0].get("estimate_complete") is True
                if change_type != "scope" or group.get("absence_verified") is not True or not complete:
                    issue("E_ABSENCE", cid, "Scope-only mapping requires verified absence and a complete opposite estimate.")
            members: list[dict] = []
            for side, ids in (("baseline", baseline), ("proposed", proposed)):
                for lid in ids:
                    if not _safe_id(lid) or lid not in lines:
                        issue("E_MAPPING", cid, "Group names an unknown line.")
                        continue
                    used[lid] += 1
                    line = lines[lid]
                    if line.get("side") != side:
                        issue("E_MAPPING", cid, "Mapped line belongs to the opposite side.")
                    if line.get("roof_location") != group.get("roof_location"):
                        issue("E_LOCATION", cid, "Mapped line roof location differs from group.")
                    members.append(line)
                    reasons.extend(held_lines.get(lid, []))
            parsed_members = [parsed[item["id"]] for item in members if item.get("id") in parsed]
            if len({item["dimension"] for item in parsed_members}) > 1:
                issue("E_UNIT", cid, "Mapped units have incompatible dimensions.")
            if len({item.get("area_basis") for item in members}) > 1:
                issue("E_AREA_BASIS", cid, "Mapped lines use different area bases.")
            if len({(item.get("geometry", {}).get("slope_included"),
                     item.get("geometry", {}).get("waste_included")) for item in members}) > 1:
                issue("E_AREA_BASIS", cid, "Mapped lines use different slope/waste inclusion states.")
            source_ids = group.get("source_ids")
            if not isinstance(source_ids, list) or not source_ids:
                issue("E_SOURCE_REF", cid, "Group evidence IDs are required.")
            elif any(not _safe_id(eid) or eid not in evidence for eid in source_ids):
                issue("E_SOURCE_REF", cid, "Group names unknown evidence.")
            scope = group.get("scope_support")
            scope_status = scope.get("status") if isinstance(scope, dict) else None
            if scope_status not in {"supported", "needs_evidence", "rejected"}:
                issue("E_SCHEMA", cid, "Unknown scope support status.")
            scope_ids = scope.get("source_ids") if isinstance(scope, dict) else None
            if (not isinstance(scope_ids, list)
                    or any(not _safe_id(eid) or eid not in evidence for eid in scope_ids)):
                issue("E_SOURCE_REF", cid, "Scope support names unknown evidence.")
            if scope_status != "supported" or not scope_ids:
                reasons.append("scope_not_supported")
                issue("R_SCOPE", cid, "Scope is not supported by supplied evidence; group held.", "review")
            coverage = group.get("coverage")
            coverage_status = coverage.get("status") if isinstance(coverage, dict) else None
            if coverage_status not in {"unknown", "accepted", "disputed", "excluded"}:
                issue("E_SCHEMA", cid, "Unknown coverage status.")
            coverage_ids = coverage.get("source_ids") if isinstance(coverage, dict) else None
            if (not isinstance(coverage_ids, list)
                    or any(not _safe_id(eid) or eid not in evidence for eid in coverage_ids)):
                issue("E_SOURCE_REF", cid, "Coverage names unknown evidence.")
            if coverage_status == "accepted":
                policy_backed = bool(coverage_ids) and all(
                    docs.get(evidence[eid].get("doc_id"), {}).get("role") == "policy" for eid in coverage_ids
                )
                if not policy_backed or not _nonempty(coverage.get("reviewer")):
                    issue("E_COVERAGE", cid, "Accepted coverage requires policy evidence and a named reviewer.")
            categories = group.get("category_ids", [])
            if not isinstance(categories, list) or any(not isinstance(x, str) or CATEGORY_RE.fullmatch(x) is None for x in categories):
                issue("E_SCHEMA", cid, "category_ids must use A-Oxx or B-Ixx identifiers.")
            if change_type == "quantity_price" and (len(baseline) != 1 or len(proposed) != 1):
                issue("E_MAPPING", cid, "Quantity/price decomposition requires one line on each side.")
            elif change_type == "quantity_price" and members:
                bline = lines.get(baseline[0], {})
                pline = lines.get(proposed[0], {})
                if (bline.get("specification") != pline.get("specification")
                        or set(bline.get("work_components", [])) != set(pline.get("work_components", []))):
                    issue("E_SPECIFICATION", cid, "Specification/scope differences require separate attribution.")
            group_data.append((group, {"reasons": sorted(set(reasons)), "scope_status": scope_status,
                                       "coverage_status": coverage_status}))

        for lid, count in used.items():
            if count > 1:
                issue("E_LINE_REUSED", lid, "A line may belong to only one group without allocation.")
        reused = {lid for lid, count in used.items() if count > 1}
        if reused:
            for group, state in group_data:
                if reused.intersection(group.get("baseline", []) + group.get("proposed", [])):
                    state["reasons"] = sorted(set(state["reasons"] + ["line_reused_across_groups"]))
        report["unmapped_lines"] = sorted(set(lines) - set(used))
        if report["unmapped_lines"]:
            issue("E_UNMAPPED", "case", "Unmapped lines are retained and complete totals are blocked.")

        computed_deltas: list[Decimal] = []
        supported_deltas: list[Decimal] = []
        with localcontext() as ctx:
            ctx.prec = 60
            for group, state in group_data:
                cid = group["claim_id"]
                baseline = group["baseline"]
                proposed = group["proposed"]
                reasons = state["reasons"]
                if any(lid not in parsed for lid in baseline + proposed):
                    reasons = sorted(set(reasons + ["numeric_value_missing_or_ambiguous"]))
                output = {
                    "claim_id": cid,
                    "baseline": list(baseline),
                    "proposed": list(proposed),
                    "roof_location": group.get("roof_location"),
                    "baseline_direct": None,
                    "proposed_direct": None,
                    "delta": None,
                    "components": None,
                    "action": None,
                    "disposition": group.get("disposition"),
                    "source_ids": list(group.get("source_ids", [])) if isinstance(group.get("source_ids"), list) else [],
                    "coverage_status": state["coverage_status"],
                    "counterargument": group.get("counterargument"),
                    "mapping_rationale": group.get("mapping_rationale"),
                    "status": "held" if reasons else "computed",
                    "scope_status": state["scope_status"],
                    "held_line_ids": sorted(lid for lid in baseline + proposed if held_lines.get(lid)),
                    "hold_reasons": reasons,
                }
                if not reasons:
                    bt = sum((parsed[lid]["total"] for lid in baseline), Decimal(0))
                    pt = sum((parsed[lid]["total"] for lid in proposed), Decimal(0))
                    delta = pt - bt
                    components = dict.fromkeys(
                        ("quantity", "price", "scope", "specification_bundle", "bundle", "rounding"), Decimal(0)
                    )
                    if group.get("change_type") == "quantity_price":
                        b, p = parsed[baseline[0]], parsed[proposed[0]]
                        components["quantity"] = Decimal(money((p["quantity"] - b["quantity"]) * b["unit_price"]))
                        components["price"] = Decimal(money(p["quantity"] * (p["unit_price"] - b["unit_price"])))
                        components["rounding"] = delta - sum(components.values(), Decimal(0))
                    else:
                        components[group["change_type"]] = delta
                    output.update({
                        "baseline_direct": money(bt), "proposed_direct": money(pt), "delta": money(delta),
                        "components": {key: money(value) for key, value in components.items()},
                        "action": "increase" if delta > 0 else "reduce" if delta < 0 else "retain_baseline",
                    })
                    computed_deltas.append(delta)
                    if state["scope_status"] == "supported":
                        supported_deltas.append(delta)
                report["groups"].append(output)

        all_groups_computed = len(report["groups"]) == len(groups) and all(
            group["status"] == "computed" for group in report["groups"]
        )
        all_lines_parsed = len(parsed) == len(lines)
        full_direct = (not blocked and all_groups_computed and all_lines_parsed
                       and not report["unmapped_lines"] and all(value is not None for value in footer_values.values())
                       and len(footer_values) == 2)
        if supported_deltas:
            report["partial_totals"]["supported_delta"] = money(sum(supported_deltas, Decimal(0)))
        if full_direct:
            baseline_direct = sum((item["total"] for lid, item in parsed.items()
                                   if lines[lid].get("side") == "baseline"), Decimal(0))
            proposed_direct = sum((item["total"] for lid, item in parsed.items()
                                   if lines[lid].get("side") == "proposed"), Decimal(0))
            report["totals"] = {
                "baseline_direct": money(baseline_direct),
                "proposed_direct": money(proposed_direct),
                "delta_direct": money(proposed_direct - baseline_direct),
                "upward_changes": money(sum((v for v in computed_deltas if v > 0), Decimal(0))),
                "downward_changes": money(sum((v for v in computed_deltas if v < 0), Decimal(0))),
                "unchanged_groups": sum(v == 0 for v in computed_deltas),
            }
            report["partial_totals"]["is_complete"] = True

        adjustments = case.get("financial_adjustments", {"baseline": [], "proposed": []})
        if not isinstance(adjustments, dict):
            issue("E_SCHEMA", "financial_adjustments", "financial_adjustments must be an object.")
            adjustments = {"baseline": [], "proposed": []}

        def financial_side(side: str) -> dict[str, Any]:
            direct = None if report["totals"] is None else Decimal(report["totals"][f"{side}_direct"])
            items = adjustments.get(side, [])
            output = {"direct": money(direct) if direct is not None else None,
                      "adjustments_specified": bool(items), "basis_status": None,
                      "adjustments": [], "total": None, "status": "held"}
            if not isinstance(items, list):
                issue("E_SCHEMA", f"financial_adjustments.{side}", "Adjustment side must be an array.")
                return output
            if not items:
                output.update({"basis_status": "no_adjustments_specified_not_verified_zero",
                               "total": money(direct) if direct is not None else None,
                               "status": "direct_only" if direct is not None else "held"})
                return output
            values: dict[str, Decimal] = {}
            known = direct is not None
            for pos, item in enumerate(items):
                ref = f"adjustment:{side}:{pos}"
                component = {"id": item.get("id") if isinstance(item, dict) else None,
                             "label": item.get("label") if isinstance(item, dict) else None,
                             "kind": item.get("kind") if isinstance(item, dict) else None,
                             "method": item.get("method") if isinstance(item, dict) else None,
                             "basis": item.get("basis") if isinstance(item, dict) else None,
                             "basis_total": None, "input": None, "calculated": None}
                output["adjustments"].append(component)
                if not isinstance(item, dict) or not _safe_id(item.get("id")) or not _nonempty(item.get("label")):
                    issue("E_SCHEMA", ref, "Adjustment needs a safe ID and nonempty label.")
                    known = False
                    continue
                aid = item["id"]
                if aid in values or any(x.get("id") == aid for x in items[:pos] if isinstance(x, dict)):
                    issue("E_DUPLICATE_ID", aid, "Adjustment IDs must be unique per side.")
                    known = False
                kind, method = item.get("kind"), item.get("method")
                if kind not in {"tax", "fee", "overhead", "profit", "credit"} or method not in {"amount", "rate"}:
                    issue("E_SCHEMA", ref, "Unknown adjustment kind or method.")
                    known = False
                if kind == "credit" and method != "amount":
                    issue("E_SCHEMA", ref, "Credit adjustments must use amount method.")
                    known = False
                basis = item.get("basis")
                if not isinstance(basis, list) or not basis or len(basis) != len(set(basis)):
                    issue("E_ADJUSTMENT_BASIS", ref, "Adjustment basis must be a nonempty unique ordered list.")
                    known = False
                    basis = []
                allowed = {"direct", *values.keys()}
                if any(value not in allowed for value in basis):
                    issue("E_ADJUSTMENT_BASIS", ref, "Basis may reference only direct and preceding adjustments.")
                    known = False
                evidence_ids = item.get("evidence_ids")
                if (not isinstance(evidence_ids, list) or not evidence_ids
                        or any(not _safe_id(eid) or eid not in evidence for eid in evidence_ids)):
                    issue("E_SOURCE_REF", ref, "Adjustment evidence IDs are required and must resolve.")
                    known = False
                amount_field, rate_field = item.get("amount"), item.get("rate")
                if method == "amount" and (amount_field is None or rate_field is not None):
                    issue("E_SCHEMA", ref, "Amount adjustment needs amount and null rate.")
                    known = False
                if method == "rate" and (rate_field is None or amount_field is not None):
                    issue("E_SCHEMA", ref, "Rate adjustment needs rate and null amount.")
                    known = False
                value = number(
                    amount_field if method == "amount" else rate_field,
                    f"adjustment:{side}:{aid}:{method}",
                    nonnegative=(method == "rate" or kind == "credit"),
                    signed=(method == "amount" and kind != "credit"),
                )
                if value is None:
                    known = False
                    continue
                if method == "rate" and value > 1:
                    issue("E_ADJUSTMENT_RATE", ref, "Rate must be a fraction from 0 through 1.")
                    known = False
                    continue
                basis_total = None
                if direct is not None and all(name == "direct" or name in values for name in basis):
                    basis_total = sum((direct if name == "direct" else values[name] for name in basis), Decimal(0))
                if basis_total is None:
                    known = False
                    continue
                calculated = value if method == "amount" else Decimal(money(basis_total * value))
                if kind == "credit":
                    calculated = -value
                values[aid] = calculated
                component.update({"basis_total": money(basis_total), "input": str(value),
                                  "calculated": money(calculated)})
            if known and direct is not None and len(values) == len(items):
                output.update({"basis_status": "explicit_adjustments", "total": money(direct + sum(values.values(), Decimal(0))),
                               "status": "computed"})
            return output

        report["financial_bridge"]["baseline"] = financial_side("baseline")
        report["financial_bridge"]["proposed"] = financial_side("proposed")

        payment = case.get("payment_scenario")
        if payment is not None:
            payment_output = {"label": payment.get("label") if isinstance(payment, dict) else None,
                              "start": None, "steps": [], "result": None, "net_payable": None,
                              "status": "held", "reason": None}
            report["financial_bridge"]["payment_scenario"] = payment_output
            if not isinstance(payment, dict) or not _nonempty(payment.get("label")):
                issue("E_SCHEMA", "payment", "Payment scenario needs a nonempty label.")
            else:
                required_evidence = payment.get("evidence_ids")
                policy_ids = payment.get("policy_evidence_ids")
                if (not isinstance(required_evidence, list) or not required_evidence
                        or any(not _safe_id(eid) or eid not in evidence for eid in required_evidence)):
                    issue("E_SOURCE_REF", "payment", "Payment evidence IDs must resolve.")
                policy_ok = isinstance(policy_ids, list) and bool(policy_ids)
                if policy_ok:
                    policy_ok = all(
                        _safe_id(eid) and eid in evidence
                        and docs.get(evidence[eid].get("doc_id"), {}).get("role") == "policy"
                        for eid in policy_ids
                    )
                if not policy_ok:
                    issue("E_PAYMENT_POLICY", "payment", "Payment scenario requires policy-role evidence.")
                current = number(payment.get("start"), "payment:start", nonnegative=True)
                scenario_known = current is not None and policy_ok
                payment_output["start"] = money(current) if current is not None else None
                steps = payment.get("steps")
                if not isinstance(steps, list):
                    issue("E_SCHEMA", "payment.steps", "Payment steps must be an array.")
                    steps = []
                step_ids: set[str] = set()
                for pos, step in enumerate(steps):
                    ref = f"payment.steps[{pos}]"
                    if (not isinstance(step, dict) or not _safe_id(step.get("id"))
                            or not _nonempty(step.get("label"))
                            or step.get("operation") not in {"add", "subtract", "cap"}):
                        issue("E_SCHEMA", ref, "Payment step ID, label, or operation is invalid.")
                        current = None
                        continue
                    if step["id"] in step_ids:
                        issue("E_DUPLICATE_ID", step["id"], "Payment step IDs must be unique.")
                    step_ids.add(step["id"])
                    ids = step.get("evidence_ids")
                    if (not isinstance(ids, list) or not ids
                            or any(not _safe_id(eid) or eid not in evidence for eid in ids)):
                        issue("E_SOURCE_REF", ref, "Payment step evidence IDs must resolve.")
                    amount = number(step.get("amount"), f"payment:{step['id']}:amount", nonnegative=True)
                    before = current
                    if amount is None:
                        scenario_known = False
                        current = None
                    elif current is not None:
                        if step["operation"] == "add":
                            current += amount
                        elif step["operation"] == "subtract":
                            current -= amount
                        else:
                            current = min(current, amount)
                    payment_output["steps"].append({"id": step["id"], "label": step["label"],
                                                    "operation": step["operation"],
                                                    "amount": money(amount) if amount is not None else None,
                                                    "before": money(before) if before is not None else None,
                                                    "after": money(current) if current is not None else None})
                live_required = not case.get("synthetic")
                related = [key for key in subjects if key == "payment:start" or key.startswith("payment:")]
                human = set(report["review_summary"]["human_confirmed"])
                if live_required and any(key not in human for key in related):
                    payment_output["reason"] = "Live payment scenario requires exact human confirmations."
                    issue("R_PAYMENT_REVIEW", "payment", payment_output["reason"], "review")
                elif current is None or not scenario_known:
                    payment_output["reason"] = "Payment scenario has unresolved inputs or policy evidence."
                else:
                    payment_output.update({"result": money(current), "status": "computed"})

        finance_held = any(
            isinstance(report["financial_bridge"][side], dict)
            and report["financial_bridge"][side]["status"] == "held"
            for side in ("baseline", "proposed")
        )
        payment_held = (isinstance(report["financial_bridge"]["payment_scenario"], dict)
                        and report["financial_bridge"]["payment_scenario"]["status"] == "held")
        if blocked:
            report["status"] = "blocked"
            report["totals"] = None
            report["partial_totals"]["supported_delta"] = None
            report["partial_totals"]["is_complete"] = False
            for group in report["groups"]:
                group["status"] = "held"
                group["baseline_direct"] = None
                group["proposed_direct"] = None
                group["delta"] = None
                group["components"] = None
                group["action"] = None
                group["hold_reasons"] = sorted(set(group.get("hold_reasons", []) + ["case_hard_error"]))
            for side in ("baseline", "proposed"):
                detail = report["financial_bridge"].get(side)
                if isinstance(detail, dict):
                    detail["direct"] = None
                    detail["total"] = None
                    detail["status"] = "held"
                    for adjustment in detail.get("adjustments", []):
                        adjustment["basis_total"] = None
                        adjustment["calculated"] = None
            scenario = report["financial_bridge"].get("payment_scenario")
            if isinstance(scenario, dict):
                scenario["status"] = "held"
                scenario["result"] = None
                scenario["reason"] = "Case has hard validation errors."
                for step in scenario.get("steps", []):
                    step["before"] = None
                    step["after"] = None
        elif not all_groups_computed or report["totals"] is None or finance_held or payment_held:
            report["status"] = "partial"
        else:
            report["status"] = "draft"
        return report
    except Exception as exc:  # defensive boundary: invalid user input must still yield a report
        issue("E_INPUT", "case", f"Input could not be reconciled: {type(exc).__name__}: {exc}")
        report["status"] = "blocked"
        report["totals"] = None
        report["partial_totals"]["is_complete"] = False
        return report
