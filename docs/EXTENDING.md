# Extend without changing the calculation engine

Use versioned JSON packs for geography, pricing, exemplars, technical guidance or carrier presentation preferences. The skill's [extension reference](../.agents/skills/xactimate-reconcile/references/extensions.md) documents the exact fields and evidence standards. `extension_examples/` contains valid drafts to copy.

```sh
python xr.py extension-validate --file extension_examples/local-context.json
python xr.py extension-add --case-dir ../private-roof-case --file extension_examples/local-context.json
python xr.py context --case-dir ../private-roof-case
```

Draft, expired, future-dated, mismatched or unverified-jurisdiction packs are not presented as applicable approved context. A pack being syntactically valid is not proof its content is correct. Reviewers must identify what they actually checked. AI synthesis and a licensed professional's review are different assertions.

## Excellent company work

Deidentify an approved memo, cover note, estimate and evidence appendix. Preserve permission to reuse them. Add an exemplar pack with a file path and SHA-256 hash, provenance, review date, roof type and a short account of why the example is strong. Explain which patterns transfer and which are peculiar to that policy, building, quote or negotiation. Do not adopt its monetary amounts or imply that a prior payment establishes entitlement on a new claim.

## Local costs

For a supplier or labor quote, record municipality, observed date, expiration, unit, currency, amount, quote source, quantities and inclusions/exclusions. Explain taxes, delivery, setup, access, mobilization and whether installation is included. Keep the actual quote in the private case. Compare it with the chosen price-list region/month and the work being priced. One quote is evidence to evaluate, not a market-wide norm.

## Code and technical details

Record the actual authority having jurisdiction, adoption/effective date, relevant building/work category, exact section or manufacturer instruction and applicability. Treat a requirement to perform work separately from the policy question of payment. A regional pack can direct investigation without pretending to resolve these questions.

## Version and evaluate

Installed pack versions are immutable. Create a new version when evidence changes. Re-run affected cases and inspect changes in context selection and document language. Retain held-out examples to detect regressions; never score success by a larger claim amount. Useful measures include traceability, material OCR accuracy, correct reductions, correct holds, duplication avoidance and an operator's ability to reproduce the intended revision.
