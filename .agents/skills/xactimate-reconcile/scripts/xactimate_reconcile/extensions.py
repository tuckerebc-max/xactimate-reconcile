"""Validation and deterministic selection for optional context extension packs."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
from pathlib import Path
import re
from typing import Any

ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}$")
DECIMAL_RE = re.compile(r"^-?(?:0|[1-9][0-9]{0,17})(?:\.[0-9]{1,8})?$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
MAX_ASSET_BYTES = 100 * 1024 * 1024


def _date(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _id(value: Any) -> bool:
    return isinstance(value, str) and ID_RE.fullmatch(value) is not None


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _shape(obj: Any, required: set[str], allowed: set[str], path: str, errors: list[str]) -> bool:
    if not isinstance(obj, dict):
        errors.append(f"{path}: expected object")
        return False
    missing = sorted(required - obj.keys())
    extra = sorted(obj.keys() - allowed)
    if missing:
        errors.append(f"{path}: missing {', '.join(missing)}")
    if extra:
        errors.append(f"{path}: unexpected {', '.join(extra)}")
    return not missing


def validate_pack(pack: dict, pack_root: Path | None = None) -> list[str]:
    """Return readable validation errors; an empty list means the pack is valid."""
    errors: list[str] = []
    root_fields = {"schema_version", "id", "version", "type", "title", "jurisdiction", "roof_types",
                   "effective_from", "effective_to", "review", "sources", "entries"}
    if not _shape(pack, root_fields, root_fields, "pack", errors):
        return errors
    if pack.get("schema_version") != "xr-extension/1.0":
        errors.append("pack.schema_version: expected xr-extension/1.0")
    if not _id(pack.get("id")):
        errors.append("pack.id: invalid safe identifier")
    if not _text(pack.get("version")) or not _text(pack.get("title")):
        errors.append("pack: version and title must be nonempty strings")
    if pack.get("type") not in {"geography", "pricing", "exemplar", "technical", "carrier"}:
        errors.append("pack.type: unsupported value")
    jurisdiction_fields = {"country", "state", "municipality"}
    if _shape(pack.get("jurisdiction"), jurisdiction_fields, jurisdiction_fields, "pack.jurisdiction", errors):
        for name in jurisdiction_fields:
            value = pack["jurisdiction"].get(name)
            if value is not None and not _text(value):
                errors.append(f"pack.jurisdiction.{name}: expected nonempty string or null")
    roof_types = pack.get("roof_types")
    if (not isinstance(roof_types, list)
            or any(not isinstance(value, str) for value in roof_types)
            or len(roof_types) != len(set(roof_types))
            or any(value not in {"shingle", "tile", "low_slope"} for value in roof_types)):
        errors.append("pack.roof_types: expected unique supported roof types")
    start = _date(pack.get("effective_from"))
    end = _date(pack.get("effective_to")) if pack.get("effective_to") is not None else None
    if start is None:
        errors.append("pack.effective_from: expected ISO date")
    if pack.get("effective_to") is not None and end is None:
        errors.append("pack.effective_to: expected ISO date or null")
    if start is not None and end is not None and end < start:
        errors.append("pack.effective_to: cannot precede effective_from")

    review_fields = {"status", "reviewer", "reviewed_at"}
    review = pack.get("review")
    if _shape(review, review_fields, review_fields, "pack.review", errors):
        if review.get("status") not in {"draft", "reviewed"}:
            errors.append("pack.review.status: unsupported value")
        if review.get("reviewer") is not None and not _text(review.get("reviewer")):
            errors.append("pack.review.reviewer: expected nonempty string or null")
        if review.get("reviewed_at") is not None and _date(review.get("reviewed_at")) is None:
            errors.append("pack.review.reviewed_at: expected ISO date or null")
        if review.get("status") == "reviewed" and (
                not _text(review.get("reviewer")) or _date(review.get("reviewed_at")) is None):
            errors.append("pack.review: reviewed status requires reviewer and reviewed_at")

    sources = pack.get("sources")
    source_ids: set[str] = set()
    source_fields = {"id", "title", "url_or_document", "accessed_date", "limitation"}
    if not isinstance(sources, list):
        errors.append("pack.sources: expected array")
        sources = []
    for pos, source in enumerate(sources):
        path = f"pack.sources[{pos}]"
        if not _shape(source, source_fields, source_fields, path, errors):
            continue
        sid = source.get("id")
        if not _id(sid):
            errors.append(f"{path}.id: invalid safe identifier")
        elif sid in source_ids:
            errors.append(f"{path}.id: duplicate identifier")
        else:
            source_ids.add(sid)
        for name in ("title", "url_or_document", "limitation"):
            if not _text(source.get(name)):
                errors.append(f"{path}.{name}: expected nonempty string")
        if _date(source.get("accessed_date")) is None:
            errors.append(f"{path}.accessed_date: expected ISO date")

    entries = pack.get("entries")
    entry_ids: set[str] = set()
    entry_fields = {"id", "title", "kind", "content", "source_ids", "amount", "unit", "currency",
                    "observed_at", "expires_at", "artifact_path", "artifact_sha256"}
    if not isinstance(entries, list):
        errors.append("pack.entries: expected array")
        entries = []
    for pos, entry in enumerate(entries):
        path = f"pack.entries[{pos}]"
        if not _shape(entry, entry_fields, entry_fields, path, errors):
            continue
        eid = entry.get("id")
        if not _id(eid):
            errors.append(f"{path}.id: invalid safe identifier")
        elif eid in entry_ids:
            errors.append(f"{path}.id: duplicate identifier")
        else:
            entry_ids.add(eid)
        if not _text(entry.get("title")) or not _text(entry.get("content")):
            errors.append(f"{path}: title and content must be nonempty strings")
        kind = entry.get("kind")
        if kind not in {"context", "cost_observation", "writing_example", "technical_note"}:
            errors.append(f"{path}.kind: unsupported value")
        ids = entry.get("source_ids")
        if (not isinstance(ids, list) or not ids
                or any(not isinstance(value, str) for value in ids)
                or len(ids) != len(set(ids))
                or any(not _id(value) or value not in source_ids for value in ids)):
            errors.append(f"{path}.source_ids: expected unique resolved source IDs")
        amount = entry.get("amount")
        if amount is not None:
            if not isinstance(amount, str) or DECIMAL_RE.fullmatch(amount) is None:
                errors.append(f"{path}.amount: expected plain decimal string or null")
            else:
                try:
                    if not Decimal(amount).is_finite():
                        errors.append(f"{path}.amount: expected finite value")
                except InvalidOperation:
                    errors.append(f"{path}.amount: expected finite value")
        for name in ("unit", "currency"):
            if entry.get(name) is not None and not _text(entry.get(name)):
                errors.append(f"{path}.{name}: expected nonempty string or null")
        observed = _date(entry.get("observed_at")) if entry.get("observed_at") is not None else None
        expires = _date(entry.get("expires_at")) if entry.get("expires_at") is not None else None
        if entry.get("observed_at") is not None and observed is None:
            errors.append(f"{path}.observed_at: expected ISO date or null")
        if entry.get("expires_at") is not None and expires is None:
            errors.append(f"{path}.expires_at: expected ISO date or null")
        if observed is not None and expires is not None and expires < observed:
            errors.append(f"{path}.expires_at: cannot precede observed_at")
        if kind == "cost_observation" and (amount is None or not _text(entry.get("unit"))
                                            or not _text(entry.get("currency")) or observed is None):
            errors.append(f"{path}: cost observation requires amount, unit, currency, and observed_at")
        artifact_path, artifact_sha = entry.get("artifact_path"), entry.get("artifact_sha256")
        if (artifact_path is None) != (artifact_sha is None):
            errors.append(f"{path}: artifact_path and artifact_sha256 must be supplied together")
        if artifact_path is not None:
            if (not isinstance(artifact_path, str) or not artifact_path
                    or Path(artifact_path).is_absolute() or ".." in Path(artifact_path).parts):
                errors.append(f"{path}.artifact_path: expected relative path without escape")
            if not isinstance(artifact_sha, str) or SHA_RE.fullmatch(artifact_sha) is None:
                errors.append(f"{path}.artifact_sha256: expected lowercase SHA-256")
            if pack_root is not None and isinstance(artifact_path, str):
                try:
                    root = Path(pack_root).resolve(strict=True)
                    target = (root / artifact_path).resolve(strict=True)
                    if not target.is_relative_to(root) or not target.is_file():
                        raise ValueError("escape")
                    if target.stat().st_size > MAX_ASSET_BYTES:
                        raise ValueError("oversized")
                    hasher = hashlib.sha256()
                    with target.open("rb") as stream:
                        while chunk := stream.read(1024 * 1024):
                            hasher.update(chunk)
                    if hasher.hexdigest() != artifact_sha:
                        errors.append(f"{path}: artifact hash mismatch")
                except (OSError, TypeError, ValueError):
                    errors.append(f"{path}: artifact path escapes pack root or is unreadable")
    return errors


def select_packs(packs: list[dict], case: dict) -> dict:
    """Select reviewed, current, matching context without applying it to claim math."""
    result: dict[str, list] = {"applicable": [], "excluded": [], "warnings": []}
    if not isinstance(packs, list):
        result["warnings"].append("Extension packs input is not an array.")
        return result
    as_of = _date(case.get("as_of")) if isinstance(case, dict) else None
    case_jurisdiction = case.get("jurisdiction") if isinstance(case, dict) else None
    if not isinstance(case_jurisdiction, dict):
        case_jurisdiction = {}
    roof_type = case.get("roof_type") if isinstance(case, dict) else None
    if as_of is None:
        result["warnings"].append("Case as_of is unknown or invalid; dated packs are excluded.")

    for pos, pack in enumerate(packs):
        ident = pack.get("id") if isinstance(pack, dict) else f"pack[{pos}]"
        reasons: list[str] = []
        errors = validate_pack(pack) if isinstance(pack, dict) else ["pack: expected object"]
        if errors:
            reasons.append("invalid: " + "; ".join(errors))
        if not isinstance(pack, dict):
            result["excluded"].append({"id": ident, "reasons": reasons})
            continue
        if pack.get("review", {}).get("status") != "reviewed":
            reasons.append("draft pack")
        start = _date(pack.get("effective_from"))
        end = _date(pack.get("effective_to")) if pack.get("effective_to") is not None else None
        if as_of is None:
            reasons.append("case date unknown")
        elif start is not None and as_of < start:
            reasons.append("future pack")
        elif end is not None and as_of > end:
            reasons.append("expired pack")
        roof_types = pack.get("roof_types", [])
        if roof_types and roof_type not in roof_types:
            reasons.append("roof type mismatch")
        jurisdiction = pack.get("jurisdiction") if isinstance(pack.get("jurisdiction"), dict) else {}
        for level in ("country", "state"):
            expected = jurisdiction.get(level)
            actual = case_jurisdiction.get(level)
            if expected is not None and actual != expected:
                reasons.append(f"{level} mismatch or unknown")
        expected_city = jurisdiction.get("municipality")
        actual_city = case_jurisdiction.get("municipality")
        if expected_city is not None and actual_city is None:
            reasons.append("municipality unknown")
            result["warnings"].append(
                f"Pack {ident} is municipality-specific but the case municipality is unknown."
            )
        elif expected_city is not None and actual_city != expected_city:
            reasons.append("municipality mismatch")
        if reasons:
            result["excluded"].append({"id": ident, "reasons": reasons})
            continue

        current_entries = []
        for entry in pack.get("entries", []):
            observed = _date(entry.get("observed_at"))
            expires = _date(entry.get("expires_at")) if entry.get("expires_at") is not None else None
            if observed is not None and as_of is not None and observed > as_of:
                result["warnings"].append(f"Pack {ident} entry {entry.get('id')} is future and was excluded.")
            elif expires is not None and as_of is not None and expires < as_of:
                result["warnings"].append(f"Pack {ident} entry {entry.get('id')} is stale and was excluded.")
            else:
                current_entries.append(entry)
        result["applicable"].append({"id": ident, "pack": pack, "entries": current_entries,
                                     "note": "Context only; no rate is automatically applied."})
    return result
