# Release validation — 2026-09-22

Version 0.1.0 is a supervised draft release. The validation environment was Linux with Python 3.12.14. No real claim, licensed Xactimate installation, Windows/macOS execution or Claude execution was included.

| Check | Observed result |
|---|---|
| New runtime suite | 50 tests passed; intake, engine, extensions, review, rendering and workflow |
| Historical C suite | 48 tests passed, separately executed from its original import root |
| B structural validation | PASS; 24 conditional arguments, 29 registered sources |
| Repository structure | PASS; 20 A categories, 24 B arguments, valid example packs |
| Skill structure | Canonical skill passed the skill-creator validator |
| Independent AI code review | Original findings fixed; all five final residual probes passed |
| Fresh-agent skill use | Produced four Markdown drafts; correctly identified only a synthetic +$500 supported item and held the complete total; AI review remained distinct from human confirmation |
| Three roof examples | Shingle +$3,050 including a $200 reduction; tile +$450; low slope partial +$500 with no complete total |
| Formats | All 12 requested Word files and 12 requested PDFs generated without renderer warnings; Markdown also generated |
| Document inspection | Word files converted successfully; all pages inspected in overviews, selected pages at full size; page-bound checks recorded separately |
| OCR smoke check | 7/7 expected numeric strings found in clean image and scan; only 1/7 in degraded image; not a real-document accuracy benchmark |

Logs and evidence: `new-tests.txt`, `baseline-c-tests.txt`, `b-structure.json`, `structure.json`, `capabilities.json`, `ocr-smoke.json`, `docx-render.json`, `page-bounds.json`, and `reviews/`. The independent review preserves early failures and its final dispositions. Read its final section for the current result. Historical workspace paths in review reports describe where those checks ran; operational files in this repository use relative paths.

The final archive is additionally checked after extraction into a folder containing spaces. Its recorded result is `clean-extraction.json`. `RELEASE_MANIFEST.json` hashes every packaged file except itself. The archive builder verifies ZIP CRC integrity.

Important limits: a passing structural or arithmetic check is not legal correctness, coverage, authenticity, professional review or proof of recovery. Local review receipts do not authenticate identities. Source prices, policy clauses, real photographs and approved company exemplars remain to be supplied and evaluated. No communications were sent.
