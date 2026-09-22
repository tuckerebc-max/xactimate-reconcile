"""Shared deterministic JSON and decimal contracts for Xactimate reconciliation."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
from pathlib import Path
from typing import Any

MAX_JSON_BYTES = 10 * 1024 * 1024
CENT = Decimal("0.01")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"Nonfinite JSON constant: {value}")


def load_json(path: str | Path) -> object:
    """Load bounded UTF-8 JSON while rejecting duplicates and nonfinite constants."""
    source = Path(path)
    try:
        size = source.stat().st_size
    except OSError as exc:
        raise ValueError(f"Cannot read JSON file {source}: {exc}") from exc
    if size > MAX_JSON_BYTES:
        raise ValueError(f"JSON file exceeds {MAX_JSON_BYTES} byte limit: {source}")
    try:
        raw = source.read_bytes()
        text = raw.decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ValueError(f"Cannot read UTF-8 JSON file {source}: {exc}") from exc
    try:
        value = json.loads(text, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}") from exc
    if not isinstance(value, (dict, list)):
        raise ValueError("JSON root must be an object or array")
    return value


def digest(value: object) -> str:
    """Return SHA-256 of canonical compact UTF-8 JSON."""
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Value is not canonical JSON: {exc}") from exc
    return hashlib.sha256(encoded).hexdigest()


def money(value: Decimal) -> str:
    """Format a Decimal as cents using the contract's ROUND_HALF_UP rule."""
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ValueError("money requires a finite Decimal")
    return format(value.quantize(CENT, rounding=ROUND_HALF_UP), ".2f")
