# Private cases and public code

Keep claim files, policy documents, addresses, photographs and real customer names in a private case directory outside this repository. The included examples are synthetic. The `.gitignore` protects common local folders but cannot prevent an operator from adding a sensitive file somewhere else. Inspect staged files before publishing to GitHub.

The Python workflow performs local OCR and rendering. It makes no network call to a model or OCR service. Opening material in Codex or another assistant remains subject to that product's own data settings. Do not describe the whole assisted workflow as offline merely because the CLI is local.

Use only deidentified, authorized examples for shared extension packs. Source hashes support change detection; they do not replace access controls, encryption, backups or permission to share a document. Apply the company's retention and access practices to private case directories and exported packages.
