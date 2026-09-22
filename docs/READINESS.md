# Release readiness — 0.1.0

**Ready for supervised demonstrations and assisted drafting. Real-claim deployment requires company validation.** The package is operable now: import documents, extract text/pages, have Codex build a source-linked ledger, reconcile it, review numeric crops, and render the four-document package.

## Demonstrated in this release

- Source preservation, native PDF extraction, local Tesseract OCR and a manual/vision path.
- Three synthetic roof examples with signed corrections, carrier-correct items and a held incomplete estimate.
- Deterministic arithmetic, explicit adjustment/payment scenarios, review fingerprints, versioned outputs and stale detection.
- Versioned extension-pack validation, location/date/roof selection and evidence-preserving installation.
- Markdown, Word and PDF generation from the same report.
- Fresh-agent use of the skill and an independent AI implementation review; findings and dispositions are retained under `validation/reviews/`.
- The new test suite, the separately preserved 48-test C suite, B's structural validator and the release structure checks. See `validation/RELEASE_REPORT.md` for recorded counts and outcomes.

## Narrow OCR result

A synthetic clean image and a synthetic scanned PDF each yielded all seven expected numeric strings in a literal-presence smoke check. A deliberately degraded, rotated image yielded only one of seven. This is useful evidence that degraded captures need image inspection and corrected readings. It is not a real-document accuracy benchmark, semantic table-mapping score or reason to trust OCR without review. Raw results and limitations are in `validation/ocr-smoke.json`.

## Still outstanding

| Item | Required next evidence |
|---|---|
| Real PDF/scanner/phone performance | Deidentified client documents with independently checked numeric and mapping oracles |
| Phoenix company excellence | Approved examples and estimator feedback on scope, evidence and prose |
| Actual local costs | Dated, comparable quotes or invoices with geographic and scope boundaries |
| Licensed Xactimate validation | Actual selectors, component inclusions, configured inspections and reconciled exports |
| Coverage and legal conclusions | The actual policy, endorsements, facts, authority and appropriate professional review |
| Other environments | Windows/macOS CI runs and direct Claude use; configuration is included but not execution evidence |
| Identity and multiuser operation | External identity/access practices; local receipts are not authenticated signatures |

The harness does not generate native ESX, determine coverage, guarantee recovery or send communications. An estimate can become more accurate by going down, remaining unchanged, or remaining incomplete. No real payment amount is assumed.
