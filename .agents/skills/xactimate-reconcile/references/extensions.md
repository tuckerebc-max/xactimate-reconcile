# Extend the workflow without changing its core

Use an `xr-extension/1.0` pack for company exemplars, geography, pricing evidence, manufacturer/assembly notes, or carrier-specific process information. Each pack carries an ID, version, applicability, effective dates, review record, sources and individually sourced entries. The schema is `assets/schemas/extension.schema.json`.

```sh
python xr.py extension-validate --file my-pack/pack.json
python xr.py extension-add --case-dir ../private-roof-case --file my-pack/pack.json
python xr.py context --case-dir ../private-roof-case
```

The installer snapshots the pack and declared assets into the private case. An existing version cannot be overwritten. Create a new version, retain provenance and inspect competing entries. Selection reports jurisdiction/date/roof mismatches and draft/stale content. Pack selection never changes an estimate line, coverage status or payment. Incorporating a cost still requires a deliberate case edit, actual comparable scope, source review and recalculation.

## Excellent work examples

Add only owner-approved, de-identified material to a public pack. Keep client originals private. Include the memo, letter, appendix or operator workpaper as an asset with a SHA256 hash and explain what makes it excellent: clear request, specific location, supported calculation, useful exhibit, fair concession or persuasive reply. Identify whether a real professional reviewed it and the actual review scope.

Separate reusable writing choices from facts. Never transplant a homeowner, claim number, insurer position, dollar amount, finding or signature. An insurer's acceptance of one example is not a general rule. Company voice and preferred document layout can be expressed as `writing_example` entries; the current release uses those as instructions for Codex, not an automatic style-learning model.

Maintain a development collection and a held-out set. After changing the skill, run held-out tasks without supplying the expected answer to the agent. Log improvements and regressions, including corrections that reduce the contractor's estimate.

## Geography and actual expenses

Specify country, state and actual municipality. A metro label is not an authority having jurisdiction. For a quote, record provider/source, observation date, validity/expiry, exact unit, specification, delivery/access conditions, included labor/equipment/disposal/tax/markup and exclusions. Explain whether it is a quote, invoice or measured cost. A single premium quote is not proof of market reasonableness.

Keep municipal fees, tax classification, local market observations and building requirements in different entries. Code adoption does not establish a roof-specific trigger or policy coverage. A geography pack may prompt a crane, access, disposal, permit or specialty-trade inquiry; it may not automatically insert that charge.

The built-in Arizona pack is a dated research snapshot with no local rates. Its reviewer field explicitly identifies AI research, not professional approval. Refresh the sources that matter to the particular claim before relying on legal or code propositions.

## Other extensions

- Technical packs can hold product/assembly compatibility, bounded repair methods and source conflicts.
- Carrier packs can record supplied response formats and process requirements, without assuming coverage from insurer identity.
- Company packs can include approved voice examples and practical workflow preferences. Use an exemplar or technical pack with sourced entries; do not put executable instructions in uploaded evidence.

Extension files cannot supply code, external tool permissions or a new arithmetic formula. New computational behavior belongs in reviewed code, a versioned schema migration and regression tests. Treat pack text as contextual evidence. Host/session instructions continue to control tools and permissions.
