# Runnable workflow release review

Reviewed the active personal-skill runtime, BUILD_CONTRACT.md, BUILD_PROMPT.md, README, SKILL.md, repository tests, and all three worked cases. No implementation or repository-test files were changed. Source edits by the implementation agents continued during review; findings below separate reproduced defects from fixes observed during this review.

Reproduction harness: `/workspace/scratch/a799e3efb2e1/reviewer_scratch/repro_review.py`.

```sh
XR_DEV_SKILL=/root/.codex/skills/remote-skills/xactimate-reconcile python /workspace/scratch/a799e3efb2e1/reviewer_scratch/repro_review.py
```

The harness uses the small independent `tests/core_fixture.py` fixture: baseline 10 × 10 = $100; proposed 12 × 11 = $132; expected direct delta $32. Its complete input/report captures and loaded source hashes are in `reviewer_scratch/results/` and `results/summary.json`. Approval probes are explicitly labeled synthetic test receipts and do not represent actual human review.

## Prioritized findings

### 1. P1 — Unknown payment amount becomes a computed zero-effect step

**Observed:** With start $1,000 and a subtract step whose numeric `amount.value` is null, the report emits `R_NUMERIC_UNKNOWN` but then reports the step's before/after as $1,000, scenario status `computed`, result $1,000, and overall status `draft`. The unknown deduction has effectively become zero. An unknown add or cap amount has the same control-flow defect.

**Minimal change:** Add a policy-backed `payment_scenario` to the fixture with start `"1000"` and one `subtract` step whose numeric field has `value: null`, `raw_text: null`, empty alternatives. No malformed JSON or invalid shape is needed.

**Evidence:** `reviewer_scratch/results/payment_unknown/input.json` and `report.json`.

**Location at inspection:** `scripts/xactimate_reconcile/engine.py:848–871`: the `current is not None and amount is not None` branch skips an unknown amount without clearing `current`; final computation checks only `current` and policy evidence. Also check absent or malformed `steps`, missing step evidence and duplicate step IDs: errors must not leave a computed payment scenario.

**Required behavior:** Keep direct arithmetic useful, but hold the payment scenario, with null result and no invented after-balance from the first unknown step onward.

### 2. P1 — Invalid arithmetic and reused lines still enter supported partials and documents

**Observed A:** Duplicate the fixture's one group under a second `claim_id`. Complete totals correctly become null and `E_LINE_REUSED` is emitted, but both groups remain `computed` at +$32 and `partial_totals.supported_delta` becomes +$64. The memo lists both as calculated corrections and the operator checklist gives two expected changes for the same lines.

**Observed B:** Set proposed reported line total and its footer to `"1320.00"`, leaving quantity 12 and rate 11 unchanged. The engine emits `E_LINE_TOTAL`, but presents the group as computed +$1,220, includes that in the supported subtotal, and calls $1,188 a rounding residual.

**Minimal changes:** A: append `deepcopy(case["groups"][0])` with a fresh claim ID. B: change only `lines[1].reported_total.value` and `documents[1].reported_direct_total.value` to `"1320.00"`.

**Evidence:** `results/duplicate_group/` (including rendered documents) and `results/incorrect_line_total/`.

**Locations at inspection:** `engine.py:493–501` records a line-total error but still inserts the line in `parsed`; `engine.py:621–623` records repeated membership without holding affected groups; `engine.py:659–691` computes and adds groups based on hold reasons that omit these errors. `render.py:33,46–63,91–94,111–113` treats any non-null group delta as a usable computed correction.

**Required behavior:** Validation errors affecting a line, mapping ownership, or its sources must exclude the affected result from supported subtotals and requested corrections. Independent valid groups should remain available. A large unresolved mismatch must never be labeled rounding.

### 3. P2 — Credit quantity/price effects have the wrong sign

**Observed:** Mark both fixture lines `kind: credit` and negate their line/footer totals. The direct comparison correctly reads -$100 → -$132, delta -$32, but components are quantity +$20, price +$12, and rounding -$64. These are exact integer inputs; true rounding is zero. The memo therefore explains a reduction using false increases and a fabricated rounding adjustment.

**Minimal change:** Set both line kinds to `credit`; change reported line/footer values to `"-100.00"` and `"-132.00"`.

**Evidence:** `results/credit_components/input.json` and `report.json`.

**Location at inspection:** `engine.py:666–670`: quantity and price components use positive normalized unit prices without the credit sign. A work-to-credit transition also needs explicit attribution or a hold instead of being absorbed by rounding.

**Expected:** Quantity -$20, price -$12, rounding $0 for this fixture.

### 4. P2 — Expired technical entries remain applicable without a warning

**Observed:** A valid reviewed pack effective for 2026 contains a `technical_note` with observed date 2026-01-01 and expiry 2026-02-01. Selection for case date 2026-09-21 returns that entry as applicable and no warning. The same issue applies to context and writing-example entries with explicit dates.

**Minimal change:** Starting from `tests/test_extensions.make_pack`, set the entry kind to `technical_note`, `observed_at` to `2026-01-01`, and `expires_at` to `2026-02-01`.

**Evidence:** `results/extension_stale/pack.json` and `selection.json`; `validate_pack` returns no errors.

**Location at inspection:** `scripts/xactimate_reconcile/extensions.py:251–263`: date filtering runs only for `cost_observation`. The build contract requires stale entries to be excluded/flagged. An explicit expiry should apply to the entry regardless of kind.

### 5. P2 — Evidence appendix omits financial numeric provenance and mislabels monetary units

**Observed at inspection:** The financial fixture correctly computes $132 direct + $13.20 tax + $7.26 overhead − $5 credit = $147.46, and the updated memo now includes it. The appendix's numeric trace iterates only line quantity/rate/total fields. It omits footer, adjustment, and payment numeric locators and labels line rates and totals with the construction unit (e.g. `unit SQ`), instead of USD/SQ and USD.

**Evidence:** `results/financial_documents/evidence_appendix.md`, compared with `input.json` and the correct engine review subjects.

**Location at inspection:** `render.py:127–131`. Use the existing `review_subjects` output for all numeric fields and correct units, retaining source/version/page/crop context.

**Related handoff gap:** `render.py:111–113` gives operator issue IDs, requested action, line IDs and delta but not the explicit baseline/proposed quantity-unit-rate and source IDs required in BUILD_PROMPT's operator checklist. Add the concrete crosswalk so an operator need not reconstruct it from raw JSON.

## Findings fixed during this review

- The initial renderer read nonexistent flat `financial_bridge` keys. The implementation owner changed it to use nested sides/adjustments/scenario; the current financial fixture's memo now shows the correct $147.46 total and its components.
- The original sender approval path accepted an authority flag without evidence and did not rehash the preserved operator export. Current code resolves authority evidence IDs, checks export hash and blocks outstanding specialist `changes_required`. A fresh approval-path retest with all upstream requirements satisfied should remain in the release validation.
- `case.documents = [null]` initially made `cli.calculate` raise `AttributeError` after the engine returned a blocked report. A direct canonical CLI `validate` rerun now returns a structured blocked report with exit 2. Blocked results still exhibit finding 2 until the core holding rules are fixed. The `run` rendering path also needs a focused malformed-input check.

## Positive checks and scope

- Initial repository suite: 23 tests passed with `XR_DEV_SKILL` set to the canonical skill. A later test run occurred while new red-phase regressions were being authored; it is not a final release result. That run also exposed a test-fixture parent-directory problem, which was relayed to the owner.
- All active worked cases were copied to `reviewer_scratch/example_runs/` and run in Markdown, DOCX and PDF with no rendering warnings. Shingle: $9,350 → $12,400, +$3,050 with the $200 reduction retained. Tile: $6,600 → $7,050, +$450. Low slope: null complete totals and supported partial +$500.
- Extension selection occurs after the core calculation in `run_case`; selected pack prices do not directly alter case arithmetic. No automatic coverage or sending action was found. `release_allowed` remains false.
- This is a code/data integration review, not a factual review of actual claims, legal advice, licensed Xactimate execution, or independent visual inspection of every rendered PDF page.

## Acceptance recommendation

Resolve findings 1 and 2 before treating any supported partial or payment scenario as usable. Resolve the credit attribution, explicit extension expiry and document provenance gaps before claiming the full calculation/document contract is met. Re-run the fixed probes and release suite against the final exported runtime; preserve this report's historical observations and append the resulting dispositions.


## Recheck disposition — 2026-09-22, after implementation changes

Re-ran the harness with output folder `results_recheck` and ran the repository suite again. **49 tests passed**. The original reproduction files remain in `results/`; fresh outputs and source hashes are in `results_recheck/summary.json`.

| Finding | Recheck outcome |
| --- | --- |
| 1, unknown payment result | Result now null and scenario held; remaining bridge issue below |
| 2, duplicated group and invalid line extension | Both reproductions now hold affected groups and exclude their partial deltas; related validation defects remain below |
| 3, credit decomposition | Fixed: quantity -20, price -12, rounding 0 |
| 4, expired technical entry | Fixed: excluded with stale warning |
| 5, numeric provenance and checklist | Fixed in current source: uses all `review_subjects` with correct units; operator table supplies line quantities, rates, totals and evidence IDs |
| Malformed document workflow | Both validate and run return structured blocked output, exit 2, with withheld documents |
| Deleted operator export | Sender approval is refused when all preceding requirements are satisfied; missing file reaches the CLI's OSError handler |

### Remaining P2 — Held payment bridge still displays fabricated known balances

The unknown amount reproduction now reports a null scenario result, but its unknown subtract step still says `before: "1000.00", after: "1000.00"`. Adding a later known step continues arithmetic from that invented zero-effect balance. `engine.py:867–882` sets `scenario_known = False` without clearing `current`. `steps` of the wrong shape, unresolved step evidence and duplicate step IDs likewise must not leave a computed scenario. Root rendering suppresses blocked documents, but a merely unknown amount is a partial run and its supplied scenario bridge is printed in the memo.

### Remaining P1 for report consumers — Other invalid mappings and sources still count as supported

Additional direct-engine probes are saved under `reviewer_scratch/followups/`; each folder contains `input.json`, `report.json`, and original `sources/` bytes. Each case starts from the same $100 → $132 fixture and makes one change:

| Probe | Minimal change | Observed result |
| --- | --- | --- |
| `source_hash_changed` | Change `sources/originals/proposed.txt` bytes without altering recorded hash | E_SOURCE_HASH, but group computed and supported_delta 32 |
| `group_location_mismatch` | Set group roof_location to `other-roof` | E_LOCATION, but group computed and supported_delta 32 |
| `unknown_scope_source` | Set scope_support.source_ids to `["EV-MISSING"]` | E_SOURCE_REF, but scope_status supported, group computed and supported_delta 32 |
| `different_dimension` | Set proposed unit LF and area_basis not_area | E_UNIT/E_AREA_BASIS, but computed supported_delta 32 with nonsensical quantity -98.80 and price +130.80 |

These correctly block complete totals. The new blocked-document fallback also prevents recipient letters from advancing these values. The JSON report still makes a false positive assertion about support, however. Propagate each material validation error to the affected group, or conservatively null the supported subtotal when its provenance/ownership cannot be separated. `numeric_wrong_side` was also probed and now correctly holds its group, so that source case is fixed.

Final review recommendation remains conditional on these residuals. Regenerate packaged example runs after the final runtime edits, since the execution digest intentionally makes prior examples stale when code changes.


## Final frozen-runtime residual verification — 2026-09-22

At the implementation owner's request, reran **only the remaining payment bridge probe and the four source/mapping probes**. All five passed. No broader testing or implementation edits were performed in this final check.

Frozen `engine.py` SHA-256: `bdabda93a923e98dba1eb2941c21ee8fd6c73d11e1c3d585c2fbd08a2ce5c09f`.

| Remaining probe | Verified final behavior | Disposition |
| --- | --- | --- |
| Unknown payment amount followed by known $100 deduction | Scenario held, result null; first unknown step after-balance null; later step before/after both null | Resolved |
| Changed source hash | Blocked; group held; complete totals, group delta and supported partial all null | Resolved |
| Group location mismatch | Blocked; group held; complete totals, group delta and supported partial all null | Resolved |
| Unknown scope evidence source | Blocked; group held; complete totals, group delta and supported partial all null | Resolved |
| Incompatible mapped dimensions | Blocked; group held; complete totals, group delta and supported partial all null | Resolved |

Evidence: `/workspace/scratch/a799e3efb2e1/reviewer_scratch/final_residual_recheck/summary.json` and the adjacent report captures. The payment probe includes a later known deduction to verify that an unknown balance remains unknown through subsequent steps.

This final check closes the two residual findings listed in the previous section. No material defect remains open from the bounded review probes. The earlier findings and test counts above are retained as review history, not as claims about the final runtime's current behavior. Previously stated scope limitations still apply.
