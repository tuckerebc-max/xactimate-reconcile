# Host adapters and capability boundary

Reviewed 2026-09-21. This package does not install a skill.

| Surface | Verified official claim | Adapter decision |
|---|---|---|
| Codex | Skills contain SKILL.md with name/description and optional resources; repository discovery includes .agents/skills. DOC-001. | Keep core Python/JSON/Markdown independent. Use the active environment's skill-creator when installation is later authorized. |
| Claude Code | Personal ~/.claude/skills and project .claude/skills are documented; host-specific frontmatter/features exist. DOC-005. | Use a separate wrapper; do not copy Codex tools or approval syntax into the core. |
| Claude API | Overview describes skill containers and surface-specific availability. DOC-002. | No API use is authorized here. Probe dependencies before any future port. |
| Session upload | This session supplied attachment bytes at an explicit local path. | Treat as case input, not persistent installation. |
| Repository access | A checked-out folder provides files. | Reading a repository does not install it or grant cloud-provider access. |

**Documentation conflict:** DOC-002 says custom skills do not sync across surfaces; DOC-005 now describes claude.ai account skill sync into signed-in Claude Code sessions. This package does not resolve that product/version distinction. Verify the target account and version; do not promise universal sync or universal lack of sync.

Capability probe: Python executable/version; readable/writable directories; native PDF tools; PDF renderer; OCR executable/language data; image tools; DOCX/PDF renderers; network restrictions; installation route. Store the result. Use subprocess argument arrays, timeouts and an allowlist in future extraction adapters; do not execute extracted document text.

Local OCR candidate command, after tool availability and input authorization are checked:

```bash
tesseract derived/page-001.png derived/page-001 -l eng --psm 6 tsv
```

DOC-004 documents TSV; selecting PSM 6 is an experiment for a uniform text block, not a reliable universal estimate-table setting. Preserve the command, engine version, dimensions, preprocessing and raw TSV. Source-image review still controls numerical use. No cloud OCR fallback is automatic.

An API key, model entitlement or session upload supplies neither a licensed Xactimate installation nor rights to its price data. The operator remains responsible for software entry/export checks.
