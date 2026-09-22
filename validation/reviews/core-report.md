# Deterministic reconciliation core report

## Completed scope

Implemented the assigned core in the canonical skill checkout:

- `scripts/xactimate_reconcile/contracts.py`
  - bounded UTF-8 JSON loading
  - duplicate-key and NaN/Infinity rejection
  - canonical JSON SHA-256 digests
  - cent `ROUND_HALF_UP` formatting
- `scripts/xactimate_reconcile/engine.py`
  - `reconcile(case, source_root, reviews=None)` returning `xr-report/1.0` for valid and invalid input
  - `review_subjects(case)` with edit-sensitive document/page/source fingerprints
  - source path, hash, page, pixel-coordinate, side, and estimate completeness checks
  - local numeric/scope holds, mapping ownership checks, signed credits, deterministic component arithmetic, footer reconciliation, partial and complete totals
  - ordered financial adjustments and explicit payment-scenario bridges
  - human/AI/synthetic/stale review accounting while keeping `release_allowed` false
- `scripts/xactimate_reconcile/extensions.py`
  - strict pack validation including dates, IDs, source references, and bounded exemplar assets
  - deterministic reviewed/current jurisdiction and roof-type selection
  - entry-level future/stale filtering for every entry kind
  - original pack retention and no automatic price application
- `assets/schemas/case.schema.json` and `extension.schema.json`
  - full Draft 2020-12 shapes with URN identifiers
  - intake page metadata, source locators, numeric fields, groups, finance, payment, and extension records
- Repository `tests/core_fixture.py`, `tests/test_engine.py`, and `tests/test_extensions.py`
  - real synthetic source bytes and recorded hashes
  - independent arithmetic expectations and malformed-input regressions

The historical `baseline_c` tree was not modified.

## Red/green record

Historical baseline before production changes:

```text
cd baseline_c && python -m unittest discover -s tests -v
Ran 48 tests in 0.208s — OK
```

Initial production red run, before the owned package existed:

```text
python -m unittest discover -s tests -p 'test_engine.py' -v
ImportError: No module named 'scripts'
FAILED (errors=1)
```

Focused initial green run:

```text
XR_DEV_SKILL=/root/.codex/skills/remote-skills/xactimate-reconcile \
  python -m unittest discover -s tests -p 'test_engine.py' -v
Ran 9 tests — OK

XR_DEV_SKILL=/root/.codex/skills/remote-skills/xactimate-reconcile \
  python -m unittest discover -s tests -p 'test_extensions.py' -v
Ran 4 tests — OK
```

Reviewer regression red run exposed credit sign attribution, invalid-total ownership, duplicate mapping, unresolved payment, malformed nested types, and extension expiry defects:

```text
XR_DEV_SKILL=/root/.codex/skills/remote-skills/xactimate-reconcile \
  python -m unittest discover -s tests -p 'test_engine.py' -v
Ran 19 tests — FAILED (failures=8)

XR_DEV_SKILL=/root/.codex/skills/remote-skills/xactimate-reconcile \
  python -m unittest discover -s tests -p 'test_extensions.py' -v
Ran 7 tests — FAILED (failures=1, errors=1)
```

Focused final green:

```text
XR_DEV_SKILL=/root/.codex/skills/remote-skills/xactimate-reconcile \
  python -m unittest discover -s tests -p 'test_engine.py' -q
Ran 19 tests — OK

XR_DEV_SKILL=/root/.codex/skills/remote-skills/xactimate-reconcile \
  python -m unittest discover -s tests -p 'test_extensions.py' -v
Ran 7 tests — OK
```

## Final verification

```text
XR_DEV_SKILL=/root/.codex/skills/remote-skills/xactimate-reconcile \
  python -m unittest discover -s tests -v
Ran 50 tests in 1.292s — OK
```

This includes engine, extensions, intake, rendering, and end-to-end workflow tests.

```text
cd baseline_c && python -m unittest discover -s tests -v
Ran 48 tests in 0.221s — OK
```

```text
PYTHONPATH=/root/.codex/skills/remote-skills/xactimate-reconcile/scripts \
  python /workspace/scratch/a799e3efb2e1/reviewer_scratch/repro_review.py
exit 0
```

The repro output confirms:

- unresolved payment amount: scenario `held`, `result: null`
- duplicate mappings: both affected groups held, `supported_delta: null`
- invalid line total: affected group held, `supported_delta: null`
- credit decomposition: quantity `-20.00`, price `-12.00`, rounding `0.00`
- stale technical entry: excluded with warning

Final reviewer follow-up regressions additionally confirm that a hard source, mapping, scope-reference, or unit-integrity error clears `supported_delta`, holds every group, and suppresses group/financial monetary outputs. An unknown payment step now clears the running balance, so later steps retain null `before` and `after` values rather than continuing from a stale amount.

Additional checks:

```text
python -m py_compile contracts.py engine.py extensions.py
exit 0

python -m json.tool assets/schemas/case.schema.json
python -m json.tool assets/schemas/extension.schema.json
both exit 0
```

A local schema walk accepted all three canonical example cases and the canonical Arizona extension pack with zero shape errors. The canonical examples reconcile as expected: shingle and tile are `draft`; low-slope is `partial` because its unknown numeric and unsupported-scope inputs remain held.

## Interface notes

- `financial_bridge` is a dictionary with `baseline`, `proposed`, `payment_scenario`, and top-level `net_payable` keys. Each estimate side contains `direct`, `adjustments_specified`, `basis_status`, `adjustments`, `total`, and `status`.
- `partial_totals.is_complete` describes direct reconciliation completeness. It can remain true when an optional payment scenario is held; the report status is then `partial` and `net_payable` remains null. Any hard validation error overrides this and suppresses all computed monetary output.
- Unknown external review subjects produce `R_REVIEW_SUBJECT` review warnings. Exact matching human confirmations alone populate `human_confirmed`; synthetic and AI confirmations remain separate.
- Applicable extension records contain `id`, the full original `pack`, a filtered `entries` list, and a context-only `note`. Renderers should use the filtered `entries` list when displaying dated entry content.
- Page metadata accepts the intake contract fields, including text-only pages with null or omitted image metadata; pixel numeric sources are still checked against recorded page width and height.
