# Operating workflow

The CLI performs storage, validation, arithmetic and rendering. Codex reads the pages, interprets the tables, selects applicable review cards and drafts the issue reasoning. A person verifies consequential source readings and approves the resulting technical package.

## Create and import

Run from the repository root, or replace `xr.py` with the installed skill's `scripts/xr.py`.

```sh
python xr.py init --case-dir ../private-roof-case --case-id ROOF-001 --roof-type shingle
python xr.py intake --case-dir ../private-roof-case --file carrier.pdf --role baseline --document-version v1 --expected-pages 6
python xr.py intake --case-dir ../private-roof-case --file contractor.pdf --role proposed --document-version v2
python xr.py intake --case-dir ../private-roof-case --file policy.pdf --role policy
python xr.py extract --case-dir ../private-roof-case --document-id D-ID-FROM-INTAKE --ocr auto
```

Repeat extraction for each relevant document ID. A later estimate is preserved but not silently selected. Use `select-estimate --document-id ...` to select it; then remap its lines. The baseline and proposed sides each need one active estimate. A single document can still be inventoried and read before a full comparison exists.

Native PDF text is preferred. Image/scanned pages can use local Tesseract; `--ocr off` leaves images for Codex vision/manual reading. `--ocr always` forces a bounded local OCR attempt. TSV confidence is not a correctness probability. Original files remain in `originals`; rendered pages, words and text remain in `derived`. Unreadable digits remain unresolved. Do not upload them to another service automatically.

## Populate the ledger

Edit `case.json` from the observed pages. Preserve the imported document IDs, hashes, roles and page metadata. Provide the complete active estimate lines, not just the desired increases. Include each document's `reported_direct_total` field. If the PDF only shows a tax-inclusive total, find or derive the direct subtotal with explicit support; do not relabel it.

Each numeric field contains `value`, `raw_text`, `alternatives`, `resolution`, `verification`, `reviewer`, `reviewed_at`, `ocr_confidence` and `source`. A source contains `doc_id`, one-based `page`, pixel `bbox` as `[left, top, right, bottom]`, `coordinate_space`, `image_size` and `method`. The rendered page metadata supplies dimensions. Use a crop containing the value, column label or enough row context to verify its meaning. Set unreviewed provenance truthfully; never copy synthetic checks into a live case.

Use decimal strings, such as `"25"` and `"450.00"`. Unknown is JSON `null`. Unit is SF, SQ, LF or EA. Distinguish roof surface from plan area. Record whether slope/waste are included. Do not request automatic geometry transforms without a separately supported measurement step.

Group corresponding lines under stable `claim_id` values. Add `title`, `observation`, `necessity`, `reply`, `requested_action` and relevant `category_ids`. `scope_support` and `coverage` are separate. An accepted coverage assertion needs the actual policy record and reviewer information; a cost correction alone is insufficient. Incomplete or rejected scope remains visible and cannot enter a supported complete request.

Use the full worked JSON cases to learn the structure; do not inherit their facts. `validate` reports errors, partial results and source-review requirements. The full schema is in `assets/schemas/case.schema.json` inside the skill.

## Review and generate

```sh
python xr.py validate --case-dir ../private-roof-case
python xr.py review-sheet --case-dir ../private-roof-case
python xr.py review-import --case-dir ../private-roof-case --file ../private-roof-case/reviews/decisions.csv --by "Actual reviewer" --kind human
python xr.py run --case-dir ../private-roof-case --formats md,docx,pdf
python xr.py status --case-dir ../private-roof-case
```

Before importing, the named person opens `reviews/source-review.html`, checks the actual crops and fills `confirm` or `reject` in the CSV decision column. A new review sheet does not overwrite a prior decision file. Use the returned filename. The importer rejects a fingerprint that no longer matches. Review records are local attestations; this package has no identity provider or electronic-signature certification.

Outputs live in a new `runs/<run-id>` directory. `CURRENT.json` identifies the latest run. A changed source, case, review record, runtime or pack makes that run stale. A failed rerun retains earlier history but does not leave it designated current. A partial run states which work remains unresolved and does not state a complete revision amount.

## Operator and sender

After a real operator creates the revised estimate in licensed Xactimate:

```sh
python xr.py operator-check --case-dir ../private-roof-case --export revised-estimate.pdf --direct-total 12400.00 --by "Actual operator" --notes "Verified item inclusions and direct subtotal; policy treatment remains separately recorded."
python xr.py package-review --case-dir ../private-roof-case --by "Actual reviewer" --kind claims --decision reviewed --notes "Describe the actual scope and findings."
```

The number above is illustrative only. Supply the real direct subtotal from the operator export. The command compares a declared subtotal; it does not extract or certify an ESX. Record a legal review only if it happened, including its limited scope. Sender approval uses `--kind sender --decision approve` and requires the package's numerical and operator conditions; synthetic packages cannot receive live approval. Recorded approval does not authorize automated sending. A person chooses recipients and sends the approved version through their normal process.

## Error recovery

| Situation | Action |
|---|---|
| Unknown digit or swapped column | Correct the field from its original image, retain alternatives, regenerate review |
| Missing page | Obtain the complete estimate and import a new version |
| Wrong unit or surface basis | Reconcile measurement method and normalize both quantity and rate |
| Duplicate charge | Inspect actual item/quote inclusions; narrow the requested operation |
| New carrier version | Import, explicitly select it, remap and review affected fields |
| Changed original hash | Restore the correct original or import the changed file as a new document |
| PDF/OCR dependency unavailable | Use available images/vision/manual reading; install documented optional tools if authorized |
| No policy or local quote | Continue technical analysis; leave policy/payment or rate conclusions unresolved |

Exit 0 means the requested local command completed; it does not mean claim approval. Exit 2 means an input/capability/refusal issue or blocked comparison. Read the returned status and diagnostics.
