# Implementation contract

Version 0.1.0. The approved BUILD_PROMPT.md is the product brief. This contract freezes the interfaces for the implementation. The end product is a supervised draft workflow, not automatic claim submission or a settlement entitlement engine.

## Ownership

The core implementer owns only canonical `scripts/xactimate_reconcile/engine.py`, `contracts.py`, `extensions.py`, canonical `assets/schemas/case.schema.json`, `extension.schema.json`, repository `tests/test_engine.py`, `test_extensions.py`, and `tests/core_fixture.py`. The integration owner owns intake, storage, review CLI, rendering, examples, documentation, packaging, and skill entry point. Both use the interfaces below. Do not spawn further agents.

Canonical skill: `/root/.codex/skills/remote-skills/xactimate-reconcile`.
Repository: `/workspace/scratch/a799e3efb2e1/xactimate-reconcile`.
Prior C implementation: repository `baseline_c/prototype/`, schema, fixtures, tests. Preserve that historical baseline; improve production modules separately.

## Task 1 Core implementation

Read this first; it defines exact interfaces. Build and test a deterministic stdlib core by adapting useful C behavior. Version is `xr-case/1.0`; preserve C field layout wherever possible. Run inherited C tests independently before changing anything. No network.

### Inputs

`engine.reconcile(case: dict, source_root: Path, reviews: list | None = None) -> dict`.
`engine.review_subjects(case: dict) -> dict[str, dict]`.
`contracts.load_json(path) -> object`: reject duplicate keys, NaN/Infinity, oversized files, JSON shape problems via readable errors.
`contracts.digest(value) -> str`: canonical JSON SHA256, sort_keys, compact UTF8.
`contracts.money(Decimal) -> str`: cent ROUND_HALF_UP.

Start with C's root fields and line/group/document/numeric-field structures. Add these explicit optional root fields: `title` string, `roof_type` enum shingle/tile/low_slope, `as_of` ISO date, `jurisdiction` object country/state/municipality/verified, `sender` object name/role/authority_status/authority_evidence_ids, `financial_adjustments` object baseline/proposed arrays, `payment_scenario` object or null, `notes` string. Root `synthetic` can be false. `price_context` is recorded only, never used to pick highest price. No implicit monetary defaults.

Document records retain C fields (including reported_direct_total) and additionally allow `pages` array (extraction metadata owned by intake), `original_name`, `mime_type`, `receipt_time`, `inspection_limits`. Document role baseline/proposed/evidence/policy/operator. Only one active baseline/proposed selected via the list; superseded originals stay manifest-only. Document dates/version must be nonempty. All document paths relative to source_root, no escape or symlink traversal outside root. Verify hashes every run, bounded reads. Page completeness applies to estimates; evidence/policy may be incomplete and reported_direct_total null. Require source doc role and estimate side agree for line/numeric references.

Numeric field retains C fields value/raw_text/alternatives/resolution/verification/reviewer/reviewed_at/source/ocr_confidence. Decimal strings or null only. Verification is an assertion (unreviewed/ambiguous/ai_checked/synthetic_checked). Human confirmation comes from external reviews, never fixture tags. Source retains doc_id/page/bbox/coordinate_space/image_size/method. Bbox uses extracted rendered page pixels; check against doc.pages[page-1] actual width/height when available. Method manual_synthetic/native_text/local_ocr/vision/manual. Non-ambiguous numeric values can compute draft arithmetic before human review; record unreviewed requirements. Missing/ambiguous values hold affected group; never zero-fill. Additional `derived_from` can be omitted; don't implement speculative transforms.

Lines retain C fields, plus optional `kind` work/credit. Work q/rates nonnegative; signed credit total allowed only for kind credit with nonnegative q/rate and total = -(q*rate). C geometry flags remain; requested transforms are held (manual reviewed geometry step required). All IDs reject leading/trailing whitespace and require `[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}`. Same rule for scope components, locations and lookup references. Descriptions/specification are free text, nonempty. A monetary correction can be signed regardless of kind.

Groups retain C fields plus optional title, observation, necessity, reply, requested_action, category_ids array (A-Oxx and B-Ixx). Scope support supported/needs_evidence/rejected, source_ids. Coverage unknown/accepted/disputed/excluded with source_ids/reviewer; accepted requires policy-role evidence + nonempty reviewer (recorded assertion, never professional certification); unknown remains normal. Runtime issues are not A/B research records. Scope-only additions/removals require absence_verified and complete opposite estimate; addition must still show scope evidence. Reject repeated line membership and many-to-many without allocation. C one-to-many/many-to-one bundles acceptable. Retain unmatched and held lines. Claim sources must resolve. Whitespace-only arguments fail. No implicit equivalence based on prose.

`review_subjects` keys are `line:<id>:quantity`, `line:<id>:unit_price`, `line:<id>:reported_total`, `document:<id>:reported_direct_total`, `adjustment:<side>:<id>:amount`, `adjustment:<side>:<id>:rate`, `payment:start`, `payment:<step-id>:amount` when those fields exist. Values: `fingerprint`, `value`, `unit`, `source`, `raw_text`. Fingerprint includes the complete numeric field, line unit/spec/location/geometry/kind/side where relevant, and referenced document hash/version/role/page metadata. Ignore arbitrary historical reviewer fields when comparing? Pick a stable documented policy: INCLUDE complete field, ensuring any edit invalidates review. External review entry: subject, fingerprint, decision confirm/reject, kind human/ai/synthetic, reviewer nonempty, reviewed_at ISO datetime. Latest entry wins; confirm with matching fingerprint is human confirmed only when kind human. Synthetic entries never human confirmed. Unknown review subject is a review warning. Synthetic mode needs no human to calculate but must remain synthetic and unsendable.

Financial adjustments array items: id, label, kind tax/fee/overhead/profit/credit, method amount/rate, amount numeric field or null, rate numeric field or null, basis array of `direct` and/or preceding adjustment IDs, evidence_ids. Rate is a fraction (0.10, not 10); bound 0..1. Supplied ordered bases only; duplicate bases prohibited. Credit method amount only, subtract nonnegative supplied amount. Empty list means no adjustments specified, NOT verified zero tax; output explicitly marks that basis. Each adjustment needs evidence IDs. Unknown fields/amounts hold that side's financial total; keep direct result. No adjustment can redefine coverage. Report exact calculation per component. Tax classification and eligibility are human-supplied evidence, not inferred.

Payment scenario is optional: label, start numeric field, evidence_ids, steps [{id,label,operation:add/subtract/cap,amount:numeric field,evidence_ids}], policy_evidence_ids. Require resolved policy evidence, all numeric human-confirmed for a live case (synthetic allowed to demonstrate), and explicit values. Calculate only an explicitly labeled scenario; report `net_payable: null` always because it is not a coverage determination. Bound nonnegative amounts and include full bridge. Missing data keeps scenario null with reason; no universal payment formula.

### Report

Return JSON-serializable object even for invalid input: schema_version `xr-report/1.0`, case_id, synthetic, status blocked/partial/draft, release_allowed false, issues list [{code,ref,message,severity:error/review}], groups array, totals dict or null, partial_totals dict, unmapped_lines, financial_bridge, source_checks, review_summary, limitations.

Computed groups preserve C report fields: claim_id, baseline/proposed IDs, roof_location, baseline_direct/proposed_direct/delta decimal strings, components {quantity,price,scope,specification_bundle,bundle,rounding}, action increase/reduce/retain_baseline, disposition, source_ids, coverage_status, counterargument, mapping_rationale. Add status computed/held and scope_status. A known but unsupported-scope group's arithmetic may be shown separately but MUST NOT enter supported partial subtotal. Prefer held group with delta null if simpler. Include held IDs/reasons. Partial totals: supported_delta (signed) or null; explicitly `is_complete:false` unless full. A duplicate/mapping/source-integrity defect affecting ownership blocks case totals; locally unknown numbers hold affected groups. Totals only if all needed lines/groups/estimate footers reconcile: baseline_direct/proposed_direct/delta_direct/upward_changes/downward_changes/unchanged_groups. Never give complete totals for missing pages or unmapped lines. Keep source-integrity issues actionable.

Review_summary includes required, human_confirmed, ai_confirmed, synthetic_confirmed, pending_subjects, stale_subjects. `release_allowed` remains false: this core produces reviewable drafts. Separate package-review receipts implemented by owner are attestations, not coverage or automatic authorization.

### Extension packs

`extensions.validate_pack(pack, pack_root=None) -> list[str]` and `extensions.select_packs(packs:list[dict], case:dict) -> dict` returning applicable, excluded, warnings. Each applicable entry includes full original pack. No automatic application of rates to estimates.

Pack shape: schema_version `xr-extension/1.0`, id safe ID, version string, type geography/pricing/exemplar/technical/carrier, title, jurisdiction {country,state,municipality} nullable strings, roof_types array, effective_from ISO date, effective_to ISO date|null, review {status draft/reviewed,reviewer:string|null,reviewed_at:date|null}, sources [{id,title,url_or_document,accessed_date,limitation}], entries [{id,title,kind context/cost_observation/writing_example/technical_note,content,source_ids,amount:string|null,unit:string|null,currency:string|null,observed_at:date|null,expires_at:date|null,artifact_path:string|null,artifact_sha256:string|null}]. Strict shapes, IDs, finite dates/values, source resolution. Relative exemplar asset path and hash verification if provided. `reviewed` pack cannot infer claim facts. Draft/expired/future/jurisdiction mismatch packs excluded with reasons; unknown case jurisdiction warns and excludes municipality-specific packs. Broad state packs may apply without city. Pack dates and cost-observation dates must be valid on case.as_of; stale entries excluded/flagged. Paths cannot escape. Selection never mutates case or combines prices. Test these behaviors and that exemplar cannot authorize payment.

### Deliverables and checks

Implement source code, full JSON schemas (not blank placeholders), meaningful tests with independent expected arithmetic. Build tests/core_fixture.py exposing `make_case(tmp_path)` returning `(case, source_root)` with true synthetic source bytes and hashes. Cover partial/unknown behavior, credits, side provenance, review invalidation, extensions and ordered finance. Record red/green commands in `/workspace/scratch/a799e3efb2e1/build_work/core-report.md`. No changes outside owned paths. Do not commit canonical personal-skill checkout; owner will validate and save the entire skill. Return concise status and interface caveats.

## Integration preflight

| Producer / consumer | Shared contract | Resolution |
|---|---|---|
| Core / intake | C-compatible documents and pixel source locators | Intake stores metadata; core verifies original bytes and shape |
| Core / review CLI | review_subjects and fingerprint receipts | Only latest exact-match confirmations count; attestations are not authenticated identity |
| Core / renderer | report field names above | Renderer never recomputes money or invents coverage |
| Extensions / skill | select_packs warnings and conditional content | Context stays separate from claimed case evidence |
| Repository / personal skill | canonical resources exported under .agents/skills | Initialize/validate canonical skill; repository is portable export |
| Documentation / tests | implemented versus required capabilities | Distinguish synthetic/Linux/host/operator evidence |

The core task is internally consistent: arithmetic can be useful before review; all documents stay drafts until separately reviewed. No external release action is implemented.
