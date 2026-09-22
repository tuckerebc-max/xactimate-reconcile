# Architecture and contracts

The model reads and reasons; deterministic Python stores, validates, calculates and renders. There is no embedded model API, hosted database or proprietary Xactimate dependency.

| Layer | Responsibility |
|---|---|
| `SKILL.md` and references | Orchestrate source reading, issue construction, writing and operator handoff |
| `intake.py`, `store.py` | Preserve originals, extract pages/OCR, maintain hashes and safe local paths |
| `contracts.py`, `engine.py` | Validate ledger semantics, reconcile signed changes, hold unsupported inputs |
| `extensions.py` | Validate and select versioned context; never apply a price automatically |
| `review.py` | Generate numeric crop review and import fingerprint-bound decisions |
| `render.py` | Render the same report into Markdown, Word and PDF |
| `cli.py` | Manage cases, immutable runs, stale detection and local review receipts |

## Case storage

Each private case contains `case.json`, `manifest.json`, `originals/`, `derived/`, `reviews/`, `extensions/` and `runs/`. A new run is built in a staging directory and renamed only after rendering succeeds and the input digest remains unchanged. `runs/CURRENT.json` points to the current completed run. Historical runs remain available. Check `status` before relying on one.

The canonical case contract is `xr-case/1.0`; report and extension contracts are `xr-report/1.0` and `xr-extension/1.0`. JSON schemas are included in the skill's `assets/schemas/`. Runtime validation also checks cross-references, hashes, page completeness, source bounds, arithmetic, mapping ownership and evidence conditions; schema conformance alone is insufficient.

## Calculation basis

Money uses decimal strings and `Decimal`, never binary floating point. Line extensions use cent `ROUND_HALF_UP`. This is the package's declared convention, not a certification that every Xactimate configuration rounds identically. The operator must reconcile any export differences.

For the same operation and unit, the difference is `q1*p1 - q0*p0`. Its quantity component is `(q1-q0)*p0`, and its price component is `q1*(p1-p0)`. Thus the quantity/price interaction is counted once. Bundles and specification changes are classified separately. A rounding component bridges cent arithmetic where necessary. Reductions remain signed.

An incomplete or unsupported group is held. A supported partial delta is not a complete proposed total. Complete totals require all necessary lines, mapping groups, source checks and estimate footers to reconcile. Empty adjustment arrays mean "not specified", not a conclusion that tax or overhead is zero. Explicit financial adjustments use ordered, named bases and evidence. Payment scenarios require explicit policy evidence and remain labeled scenarios; `net_payable` is never inferred.

## Integrity and trust

Hashes detect changes, not document authenticity. Review records are local attestations, not authenticated signatures. Document text and extension content remain untrusted data. The CLI does not execute supplied scripts, follow claim-document URLs or upload documents for OCR. Case directories are intended for one operator at a time; concurrent editing is detected during rendering but there is no multiuser locking service.
