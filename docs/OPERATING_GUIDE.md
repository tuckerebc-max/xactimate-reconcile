# Operator guide

Start with the demonstration in README. For live work, read the bundled skill's [workflow](../.agents/skills/xactimate-reconcile/references/workflow.md), which documents every local command. Paths below are relative to the repository root.

## Intake and preparation

Create a case with `python xr.py init --case-dir ../private-roof-case --case-id ROOF-001 --roof-type shingle`. Supply actual estimate versions, the policy and endorsements when available, roof measurements, damage photographs, manufacturer instructions, relevant permit/code evidence and quotes or invoices. Missing materials become explicit requests; they do not prevent an initial inventory.

Import each document with `intake`, supplying its role and known expected page count. Extract it with `extract`. Original bytes remain separate from rendered pages, OCR text and word coordinates. If the source is a photograph, retain the original; read the normalized derivative using its recorded coordinates. OCR confidence is a triage signal, not proof that a digit is right.

Codex then populates `case.json`: document totals, individual line quantities/rates/totals, evidence, and groups that identify equivalent physical operations. Use the synthetic examples as schema demonstrations, not as prices or claim facts. Resolve one-to-many bundles explicitly. Do not convert SQ to SF without correcting the rate basis, or apply pitch/waste to a quantity that already includes it.

Verify the actual municipality and applicable date. A Phoenix mailing address or the word "Arizona" does not establish which building department or code edition governs the property. Compare the same estimate basis: direct costs, tax, overhead/profit, depreciation, deductible and payments belong in separate fields and explanations.

## Source and issue review

Run `validate` after mapping. Fix blocked errors; explain partial results. Use `review-sheet` to generate a source-crop viewer and decision CSV. A real reviewer examines the numbers and imports their own decisions with `review-import --kind human`. AI checking uses `--kind ai`. Review fingerprints include the numeric field and its source context; changing those inputs invalidates that reading.

Review all applicable cards in the skill's [20-category inventory](../.agents/skills/xactimate-reconcile/references/review-cards.md). Each issue needs an observation, repair necessity, calculation, supporting evidence, plausible carrier response, fair reply and precise action. Separate a technical cost proposition from coverage and role authority. Document concessions and removals as carefully as additions.

The two specialist review lenses are: claims/estimating (measurements, item inclusions, causation, repairability, pricing, duplication) and legal/authority (actual policy terms, applicable law, sender role, unresolved disputes). An AI pass must be labeled AI. Record a licensed person's review only if it actually occurred.

## Generate and hand off

Run `python xr.py run --case-dir ../private-roof-case --formats md,docx,pdf`. Open the Word/PDF files and inspect every page for clipped tables, missing exhibits and inaccurate wording. All amounts originate in one report. Changing that report or a generated document makes the run stale; edit the underlying ledger and regenerate.

Provide the operator checklist to someone using licensed Xactimate. They verify actual selectors and inclusions, pricing region/month, quantities, taxes and adjustments, notes and exports. Record the exported PDF/ESX and operator-declared direct subtotal with `operator-check`. This is not an ESX parser.

After the appropriate people have reviewed the package, `package-review` records limited local attestations. It does not authenticate identity, establish coverage or transmit anything. The sender chooses recipients and sends the correct approved version through the company's normal process.
