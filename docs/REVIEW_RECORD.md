# Build decisions and review record

The implementation uses one core implementer and a coordinating integration owner, followed by a fresh independent implementation review and a separate fresh-agent workflow use. These are AI checks, not licensed legal, public-adjusting or estimating signoffs.

| Decision | Reason |
|---|---|
| Keep model interpretation separate from Python arithmetic | OCR text is not a verified estimate ledger |
| Keep A/B conditional and preserve C baseline | Research categories guide investigation; synthetic prototype evidence is not production assurance |
| Declare decimal rounding and direct-cost basis | Comparisons and policy payment must not be conflated |
| Hold unknown values and unsupported scope | Prevent an apparent complete amount from incomplete evidence |
| Preserve signed reductions | Accuracy can favor the carrier or reduce a proposed charge |
| Select, but never auto-apply, extension prices | Local examples and quotes need claim-specific applicability |
| Use source fingerprints and output hashes | Later source or runtime changes must invalidate stale drafts |
| Keep operator export check explicitly declarative | No licensed integration or ESX parser was provided |

The independent review identified defects in payment missing-value propagation, signed credit attribution, duplicate mapping, invalid-line partial totals, expired entries, nested malformed inputs, financial rendering, numeric trace units and operator handoff detail. Fixes and regression outcomes are recorded in the release report. The first review report is retained as a historical artifact; read its dispositions before treating every original finding as still open.
