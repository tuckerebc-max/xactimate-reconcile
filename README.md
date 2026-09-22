# Xactimate Reconciliation

A Codex skill and local Python workflow for comparing residential roof estimates, preserving source evidence, checking arithmetic, and preparing a documented supplement request. Version **0.1.0 — supervised draft release**.

The package handles shingle, tile, and low-slope roofs. Its research includes 20 estimation review categories and 24 conditional Arizona arguments. None is an automatic charge or a coverage entitlement.

## Start in Codex desktop

1. Unzip this repository and open its folder as a Codex project. Keep the included `.agents` folder; it contains the project skill.
2. Give Codex this instruction:

   > Use $xactimate-reconcile. Run the shingle demonstration first. Then help me reconcile my carrier and contractor roof estimates, keeping the original files and unresolved questions visible. Produce the reconciliation memo, cover letter, evidence appendix, and Xactimate operator checklist. Keep the live case in a separate private folder.

3. If the skill is not discovered, ask Codex to read `.agents/skills/xactimate-reconcile/SKILL.md` explicitly. This project does not need an account credential, API key, or a hosted service.

Python 3.10 or later is required. Use `python3` instead of `python` if that is your system's command.

```sh
python xr.py doctor
python xr.py demo --roof shingle --case-dir ../roof-demo
python xr.py run --case-dir ../roof-demo --formats md
```

For PDF reading, source images, Word documents and PDF outputs, install the optional dependencies in a virtual environment:

```sh
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements-optional.txt
python xr.py run --case-dir ../roof-demo --formats md,docx,pdf
```

Scanned/image OCR can use a separately installed Tesseract executable. Codex can also inspect the rendered images and populate the ledger by vision. The Python CLI does not interpret an arbitrary estimate into verified line items automatically.

## What you receive

Each run creates a versioned folder with four documents in the requested formats, plus its calculation report, case snapshot, selected context, and output hashes:

| Document | Purpose |
|---|---|
| Reconciliation memo | Quantifies each supported difference; records contrary evidence and unresolved scope or policy questions |
| Cover letter | Makes a polite, specific request on the supported comparison basis |
| Evidence appendix | Connects issue and line IDs to preserved documents, pages, crops and numeric readings |
| Operator checklist | Describes changes a licensed Xactimate operator must implement and verify |

Both increases and reductions remain visible. Unreadable values, missing pages, unsupported additions and unresolved units cannot silently become zero or a complete request amount. A later edit makes earlier output stale.

## Three worked examples

The examples and their amounts are fictional teaching cases, not Phoenix price guidance.

| Case | Direct-cost comparison | Behavior demonstrated |
|---|---|---|
| Shingle | $9,350 → $12,400; net +$3,050 | Quantity and price effects; $200 reduction for excessive flashing |
| Tile | $6,600 → $7,050; net +$450 | Retains the supported repair approach and unchanged carrier items |
| Low slope | Complete proposed total withheld | Shows a supported +$500 difference while concealed substrate remains unmeasured |

Use `demo --roof tile` or `demo --roof low_slope` with a new destination. Open `examples/` for generated sample documents.

## Add your company's knowledge

Versioned packs support approved work examples, city context, local quotes, technical guidance and carrier-specific presentation preferences. Packs are selected by location, date and roof type. They never silently replace claim prices or override the source ledger. See [EXTENDING.md](docs/EXTENDING.md) and `extension_examples/`.

## Documentation

- [Operating guide](docs/OPERATING_GUIDE.md): intake, source review, comparison, output and handoff.
- [Architecture and data](docs/ARCHITECTURE.md): where records live and how calculations work.
- [Readiness and limitations](docs/READINESS.md): what has and has not been demonstrated.
- [Provenance](docs/PROVENANCE.md): A, B and C research, method sources and inherited code.
- [Evaluation and maintenance](docs/EVALUATION.md): repeatable checks and future company examples.
- [Privacy](docs/PRIVACY.md): keeping claim files out of a public repository.

## Development

```sh
python -m unittest discover -s tests -v
python tools/check_baseline.py
```

The second command preserves the historical C prototype tests; it is not a test of the new workflow. CI describes Linux, macOS and Windows jobs. Only platforms actually listed in the validation report were executed for this release.

This package neither operates licensed Xactimate nor generates a native ESX. It prepares the operator handoff and can compare an operator-declared direct subtotal with the calculated revision. A person must verify actual item inclusions, estimate settings, exports, policy treatment, role authority and the final communication. It never sends a claim packet automatically.
