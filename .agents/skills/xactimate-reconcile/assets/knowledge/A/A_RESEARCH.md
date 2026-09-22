# A — Xactimate accuracy and roofing estimate differences

**Research date:** September 21, 2026. **Scope:** Phoenix-area residential shingle, tile and low-slope roofing. **Status:** Research handoff complete; every claim-specific correction still requires evidence.

This packet contains exactly 20 review categories in **A_OPPORTUNITIES.json** and 29 primary-source records in **A_SOURCES.json**. No actual estimate, policy, roof record or supplier quote was supplied. The illustrative $20,000 and $35,000 estimates are not established costs or a target increase. Supported corrections can move either estimate up or down.

## Five strongest findings

1. **A published price is a benchmark that may need a documented job-specific adjustment.** Verisk's methodology explicitly addresses differences in job size, complexity, access and location. It also provides a process for questioning researched prices. A higher contractor quote still needs a comparable scope, date, market and inclusion analysis. [A-S25]
2. **The estimate should be checked at the component and physical-work level.** Xactimate exposes item detail and labor/material/equipment components. This permits an inclusion check before adding accessories, separate labor, minimums or disposal. Actual contents must be read in the licensed installation; no proprietary item inclusions have been assumed here. [A-S03] [A-S04] [A-S06]
3. **Repair extent and roof assembly are evidence questions.** Tile guidance describes individual repairs, while the low-slope restoration specification identifies conditions and preparation relevant to restoration suitability. Neither establishes whether this customer's roof needs repair, recoat or replacement. [A-S19] [A-S20] [A-S26]
4. **Phoenix permit costs are conditional.** The City's currently linked brochure lists some same-material reroofing as exempt, but it is marked Rev. 2/20. Confirm the actual scope against the applicable current code and authority having jurisdiction (AHJ); the adoption page alone does not establish an upgrade trigger. [A-S16] [A-S17]
5. **Software checks do not resolve the whole dispute.** Variation compares pricing against a checkpoint. A separate line/scope ledger is needed to compare two estimates. Software inspection and depreciation controls do not prove physical damage, coverage or the amount presently payable. [A-S09] [A-S12] [A-S14]

## Ranked review priorities

**Method:** The ranking below is analyst judgment about potential cost exposure and the value of checking an assumption early. It is not an empirical frequency ranking, recovery probability or dollar forecast. Roof type, evidence and an actual estimate can change the order. First normalize the comparison using A-O20; repeat that gate at the end.

| Priority | Category | Why it can matter; first evidence to obtain |
| --- | --- | --- |
| 1 | A-O01 — Geometry and slopes | Area errors propagate across several operations. Obtain a face-labelled takeoff, pitch readings and the aerial report's assumptions. |
| 2 | A-O04 — Repairability and replacement extent | A repair-versus-facet/system decision changes scope substantially. Obtain a documented feasible-repair assessment and alternatives. |
| 3 | A-O03 — Material and assembly specification | A wrong product or assembly rate repeats across the job. Identify the existing product and a supported replacement specification. |
| 4 | A-O08 — Low-slope assembly | Coating, patching and membrane/insulation replacement have different scopes. Identify the system, condition and compatible repair requirements. |
| 5 | A-O06 — Underlayment | A necessary replacement may affect substantial area and access work. Verify layers, slope, condition and applicable installation detail. |
| 6 | A-O07 — Tile lift/reset and salvage | Reuse and access affect labor and materials. Inventory sound tiles, damaged tiles, fastening and documented handling losses. |
| 7 | A-O18 — Local material/labor overrides | An evidenced rate difference multiplies across quantity. Obtain dated comparable quotes and explain exclusions. |
| 8 | A-O17 — Price-list market/date | Different baselines can create a broad apparent gap. Record exact list IDs, dates, location and checkpoint before repricing. |
| 9 | A-O05 — Tear-off and layers | Extra verified layers change removal work. Record exposed layers and what the base removal line already covers. |
| 10 | A-O15 — Solar/HVAC detach-reset | Necessary specialty work can be a discrete cost. Document physical interference and obtain a scope-specific trade quote. |
| 11 | A-O11 — Decking/substrate | Exposed defects can change scope; concealed quantities remain pending. Obtain located photos, measurements and cause/necessity evidence. |
| 12 | A-O02 — Waste, starter and ridge | Repeated small allowances accumulate. Reconcile material takeoffs with automatic settings and separate accessory items. |
| 13 | A-O10 — Flashings and penetrations | Features accumulate measured work. Inventory each valley, wall, curb, chimney and penetration; assess reuse. |
| 14 | A-O14 — Access, height and staging | Unusual access can affect productivity. Prove the incremental constraint and costs beyond included setup. |
| 15 | A-O19 — Tax, O&P and minimums | Bases and allocation can materially change totals. Verify classification, included costs and the job-specific rationale. |
| 16 | A-O09 — Edge metal and closures | Perimeter quantities are measurable. Map lengths and show why repair, reset or replacement is necessary. |
| 17 | A-O13 — Drainage and transitions | A damaged feature or necessary tie-in may be omitted. Separate those from maintenance or pre-existing ponding. |
| 18 | A-O16 — Disposal and permits | Net hauling or an applicable fee may be missing. Check removal inclusions, tickets/quotes and the actual permit trigger. |
| 19 | A-O12 — Ventilation | Affected components may need work. Distinguish repair/integration from an elective whole-attic redesign. |
| Gate | A-O20 — Valuation, payment and duplicates | Run first and last. RCV-versus-ACV, holdback or payment comparisons can explain a large gap without adding construction work. |

Each JSON record contains a calculation approach, evidence requirements, the strongest plausible carrier response, a supported reply, defeating conditions, duplicate-cost risk and a Xactimate action. All amounts remain null until claim-specific evidence supports them. The JSON's review_priority for A-O20 is an indexing convenience; its workflow_timing explicitly requires the opening and closing gate.

## Ten-step Xactimate operator checklist

These are recommended review controls. The cited sources establish the specified software capabilities; they do not make every recommended review action a Verisk requirement. Menu references are for the documented desktop/X1 workflows unless stated otherwise.

1. **Preserve and normalize the source estimates.** Retain original PDFs/ESX files, versions, dates, roof locations, measurements and inspection limitations. Record quantity units, specifications and the financial basis of each total. Compare like scope and gross replacement-cost value (RCV) before reconciling actual cash value (ACV), depreciation or payments. [A-S14]
2. **Record pricing and checkpoint settings.** In Claim Info > Parameters, record the exact project and checkpoint price lists. Lists can be requested by city/ZIP or name. Keep the original comparison and show any alternative date/market as a separate scenario. The help pages do not prescribe one universally correct claim month. [A-S02] [A-S13]
3. **Reconcile Sketch with the measured roof.** Check each face, pitch, boundary, opening and relevant length. Roof Properties accepts slope-rise by lettered face. Do not apply a slope factor to an area already measured on the roof surface. Explain differences from any aerial report. [A-S22]
4. **Inspect every disputed item's definition and components.** Use Estimate Items > Items > Search > Click for detail and the Components view. Record selector/activity, unit, formula, description and inclusions from the licensed system. Match one physical operation across both estimates, including grouped lines where necessary. [A-S03] [A-S04]
5. **Review automation and accessories.** A macro is a saved item list; load into the intended group and check its output. Reconcile manual formulas, automatic waste, starter and ridge quantities. XactScope prompts depend on material and settings; its felt-inclusion example is not a universal roofing rule. [A-S05] [A-S10] [A-S11] [A-S24]
6. **Attach an item-level evidence note.** F9 opens line notes and supports document/image attachments. For each issue, state location, observed condition, exhibit IDs, quantity derivation, existing allowance, requested operation and the inclusion check. This note structure is our proposed control. Confirm that the recipient can see the attachments. [A-S07]
7. **Document supported price changes and financial settings.** Unit Price controls expose price details, tax/O&P flags, trade and minimum group. Attach comparable quotes and isolate what changed. Check labor minimums once per applicable group and prevent duplicate callout charges. Treat tax/O&P/coverage as separate evidence questions. [A-S06] [A-S08]
8. **Run software inspection.** Complete > INSPECT runs the documented estimate check. Our operator control is to correct material issues or record a justified allowed exception. If paid XactXpert reporting is activated, preserve applicable scorecard/audit and bypass information after the configured inspection/upload workflow. Neither check is a physical inspection. [A-S12] [A-S23]
9. **Produce the comparison and preserve outputs.** Use Variation to disclose checkpoint price differences. Separately retain the carrier-versus-contractor scope ledger, signed deltas and supporting exhibits. Close the project before desktop ESX export; retain readable estimates and check what exported reports actually include. [A-S09] [A-S13] [A-S15]
10. **Resolve remaining physical questions through a focused reinspection.** Identify the disputed faces/components, competing explanations, evidence needed and qualified person to assess them. Keep concealed work and uncertain handling loss pending. Do not improvise unsafe or destructive tests. This is a proposed evidence procedure, not a software function.

## Calculation and duplicate-cost discipline

**Units:** SF means square feet; SQ means 100 square feet; LF means linear feet. Convert only compatible dimensions, and convert the rate consistently. Keep original values and normalized values together. Photographed or OCR-read quantities need source-image verification before they support a request.

For one unchanged specification and operation, let q0 and p0 be the existing quantity and price; let q1 and p1 be the supported revised values:

- Direct-cost change = q1 × p1 − q0 × p0.
- Quantity effect = (q1 − q0) × p0.
- Price effect = q1 × (p1 − p0).

Those two effects sum to the direct-cost change without counting their interaction twice. Keep line rounding and any residual visible. If specification or scope changes, use a matched-work group and a complete alternative-scope comparison; do not force an artificial per-unit decomposition.

**Synthetic arithmetic example only; these are not Phoenix prices:** 20 SQ at $400 gives $8,000. A supported 25 SQ at $450 gives $11,250. The difference is $3,250: $2,000 quantity effect and $1,250 price effect. The revised $11,250 replaces the existing $8,000 allowance; it is not an $11,250 supplement. Reversing the comparison yields a $3,250 reduction. No coverage, markup or payment is implied.

For roof geometry, plan area × sqrt(1 + (rise/run)^2) applies only to a planar face whose starting area is horizontal projection. A pitch expressed as rise per 12 uses run = 12. Complex roofs require verified face geometry. Actual surface area must not be slope-adjusted again.

Use a unique component/activity/location identity. Attribute a proposed change to one category, even when several categories helped identify it. Examples needing overlap review: full tile replacement plus lift/reset of those tiles; a bundled boot plus its integral flashing; tear-off disposal plus the same hauling allowance; an all-in trade quote plus its included labor or crane; automatic waste plus a manual waste factor; repair and replacement of the same area. These are review risks, not claims about any proprietary line's contents.

Maintain three separate ledgers:

| Ledger | Contents | Release condition |
| --- | --- | --- |
| Construction comparison | Scope, quantities, specifications and direct rates; signed additions and reductions | Each changed operation has measurements, cost support and a duplicate check |
| Estimate financial reconciliation | Applicable taxes, general O&P, credits and gross RCV | Bases and rates are supplied and independently justified; no automatic percentages |
| Policy/payment reconciliation | Valuation method, allowed depreciation, ACV, deductible, limits, holdback conditions and prior payments | Actual policy and payment record support the treatment; unresolved terms remain unknown |

Missing information is unknown, not zero. No claim-specific net payment can be calculated from this packet.

## Adversarial review: arguments that must survive

| Proposed adjustment | Strongest plausible response | What would resolve it |
| --- | --- | --- |
| Replace a facet or whole roof | A durable local repair is feasible | A documented repair method assessment, compatibility/availability evidence and narrower alternatives; concede feasible repair |
| Raise prices for inflation | The existing list/allowance already reflects the relevant market | Exact baselines and comparable dated supplier/trade evidence; show the incremental difference only |
| Add underlayment, accessories or disposal | The selected item or quote already includes it | Licensed component detail and quote exclusions; remove any duplicate |
| Add tile handling losses | The percentage is speculative or includes contractor-caused breakage | Located pre-work condition, salvage plan and observed/justified handling records; keep uncertain quantities contingent |
| Charge a permit or code upgrade | The work is exempt or does not trigger that requirement | Current AHJ determination for address, scope and code edition, followed by separate coverage analysis |
| Replace concealed decking | No cause or quantity is established | Exposure photos, measured area and qualified necessity/cause analysis; retain an open item until then |

Technical context: TRI/Eagle describe tile repair; GAF steep-slope guidance identifies causes other than the alleged storm for some observed conditions. These sources support testing alternatives rather than assuming a loss mechanism. [A-S18] [A-S19] [A-S20]

## Source conflicts and qualifications

- **Phoenix brochure age:** A-S17 is live but dated February 2020. Use it as a reason to investigate permit applicability, not as a definitive exemption under the 2024 PBCC. Its ambiguous layer wording is not converted into a reroofing limit here. [A-S16] [A-S17]
- **GAF LIBERTY slope:** The installation/system materials and 2026 sell sheet indicate a 1/4:12 lower bound, while the cap-sheet webpage indicates 1/2:12. Product/assembly applicability or an editorial inconsistency may explain the difference; this research does not resolve it. Obtain current product-specific confirmation rather than choosing the more convenient number. [A-S21] [A-S27] [A-S28] [A-S29]
- **Low-slope transfer:** Carlisle's July 2026 restoration specification adds useful assessment, adhesion, moisture and substrate-compatibility questions for selected foam/asphaltic/single-ply systems. It is a commercial product specification; residential applicability and the actual roof product still need verification. [A-S26]
- **Two Verisk documents:** The original methodology summary A-S01 and the accessible methodology paper A-S25 are distinct 2023 documents. The latter's accessible URL does not establish a newer edition. Preserve the former's narrower overhead distinctions without treating them as a coverage or markup entitlement. [A-S01] [A-S25]
- **Software versus policy:** A software control, macro output or scorecard is not approval of a repair or an obligation to pay. Item inclusions, current local prices and deployment-specific features require the licensed installation.

## Five most important gaps

1. **The claim record:** both complete estimates, policy/endorsements, loss date, versions, payments and any prior supplement decisions.
2. **Physical scope and cause:** verified measurements, roof access/inspection limits, located photos, prior condition, repair feasibility and qualified evaluation of concealed work.
3. **Licensed estimating detail:** actual Phoenix-area list IDs/months, selectors, activity definitions, component inclusions and documented local quotes.
4. **Product and AHJ applicability:** exact shingle/tile/foam/membrane/coating system, current instructions, actual jurisdiction and triggered requirements. The generic low-slope gap is narrowed, not fully closed for an unidentified residential roof.
5. **Financial and policy authority:** tax classification, O&P justification, depreciation treatment, coverage conditions and current payable balance. These belong in the policy/legal workstream; no universal entitlement was established here.

## Method and validation

This assignment builds on the earlier same-day primary-source pass, with two bounded Luna checks for software and roofing evidence. Sources A-S02 through A-S29 were reopened or newly inspected in this assignment. A-S01 was inspected in the earlier pass but its fresh reopen failed; that status is explicit in the register. Root independently downloaded and inspected the accessible Verisk methodology, Phoenix page/brochure, TRI manual, Eagle article and Carlisle specification. The search-service failure in the root session did not prevent those public-source checks or the Luna verifications.

The final check verifies exactly 20 unique category IDs; all required fields; unique source IDs; every category's source references; all 20 ranking positions; preserved null claim amounts; and the synthetic arithmetic and unit-conversion examples. The report distinguishes source-supported statements from proposed operator controls and claim-specific hypotheses. No live Xactimate environment, actual claim, roof inspection or professional acceptance test was performed. No insurer was contacted and no claim was submitted.

## Source links

The JSON register includes publisher, date, precise locator, supported claim, limitation and retrieval status for each item. Links below resolve the bracketed source IDs in this memo.

[A-S01]: https://eservice.xactware.com/esc/showme/PDF/2023/WhitepaperPricingMethodologySummary.pdf "Pricing Methodology Summary"

[A-S02]: https://xactware.helpdocs.io/l/enUS/article/rub4zm9yj6-download-price-list-x-1 "Downloading price lists"

[A-S03]: https://xactware.helpdocs.io/l/enUS/article/5yvrJm6kxW-view-item-details "View item details in X1"

[A-S04]: https://xactware.helpdocs.io/l/enUS/article/nFe5yTyJCn-view-or-adjust-line-item-components "View or adjust line item components in X1"

[A-S05]: https://xactware.helpdocs.io/l/enUS/article/bmxus6tpmi-xact-scope-roof-and-exterior-prompt-dependencies "XactScope roof and exterior prompt dependencies"

[A-S06]: https://xactware.helpdocs.io/l/enUS/article/8fF4NT38IM-modify-the-item-unit-price "Modify the item unit price in X1"

[A-S07]: https://xactware.helpdocs.io/l/enUS/article/slcJXA1qsU-attach-notes-images-or-sound-files-to-a-line-item "Attach or delete notes, images, or sound files to a line item in X1"

[A-S08]: https://xactware.helpdocs.io/l/enUS/article/7HbYf3a1oK-apply-labor-minimums-for-a-line-item "Apply labor minimums for a line item in X1"

[A-S09]: https://xactware.helpdocs.io/l/enUS/article/5KboYMrf5t-variation-reports "Variation Reports"

[A-S10]: https://xactware.helpdocs.io/l/enUS/article/8St4RQFshL-create-a-macro "Create a macro in Xactimate desktop"

[A-S11]: https://xactware.helpdocs.io/l/enUS/article/ZaDeAQ4kuL-load-a-macro "Load a macro in Xactimate desktop or online"

[A-S12]: https://xactware.helpdocs.io/l/enUS/article/qU92vhqg6j-run-an-inspection-for-the-entire-estimate "Run an inspection for the entire estimate in desktop"

[A-S13]: https://xactware.helpdocs.io/l/enUS/article/rdbBQFEZqe-use-a-checkpoint-price-list "Use a checkpoint price list in desktop"

[A-S14]: https://xactware.helpdocs.io/l/enUS/article/nznu9esza7-depreciation-in-xactimate-desktop "Depreciation in Xactimate desktop"

[A-S15]: https://xactware.helpdocs.io/l/enUS/article/8izugze23w-export-a-project-to-your-computer-from-xactimate-desktop "Export a project to your computer from Xactimate desktop"

[A-S16]: https://www.phoenix.gov/administration/departments/pdd/tools-resources/codes-ordinance/building-code.html "Building Construction Codes | City of Phoenix"

[A-S17]: https://www.phoenix.gov/content/dam/phoenix/pddsite/documents/trt/external/dsd_trt_pdf_00823.pdf "How to Obtain a Residential Permit Brochure"

[A-S18]: https://www.gaf.com/en-us/document-library/documents/installation-instructions-%26-guides/pro-field-guide-for-steep-slope-roofs-resgn103.pdf "Steep-Slope Pro Field Guide"

[A-S19]: https://www.tileroofing.org/uploads/1/4/9/0/149044128/tri_alliance_2024_guide_iapmo_041725.pdf "Concrete and Clay Roof Tile Installation Manual"

[A-S20]: https://eagleroofing.com/2019/04/how-to-properly-replace-damaged-concrete-roof-tiles/ "How to Properly Replace Damaged Concrete Roof Tiles"

[A-S21]: https://documents.gaf.com/installation-instructions-&-guides/liberty-sbs-self-adhering-installation-instructions-trilingual-reslb504-(9-22).pdf "LIBERTY SBS Self-Adhering Installation Instructions"

[A-S22]: https://xactware.helpdocs.io/l/enUS/article/j38YWJcCJV-change-the-slope-of-a-roof "Change the slope of a roof in X1"

[A-S23]: https://xactware.helpdocs.io/l/enUS/article/doiax1kjeb-xact-xpert-reports "XactXpert Reports"

[A-S24]: https://xactware.helpdocs.io/l/enUS/article/rasph9dmn9-auto-waste-calculation-workflow "Calculating roof waste"

[A-S25]: https://www.verisk.com/49c07f/siteassets/media/downloads/property-estimating/pricing-research-methodology.pdf "Pricing Research Methodology"

[A-S26]: https://ccm-p-001.sitecorecontenthub.cloud/api/public/content/be3bee6a8a6e440eaa70201bffb9f803?download=true&v=ec98d348 "X-Tenda Coat Coating System — Restoration Coatings"

[A-S27]: https://www.gaf.com/en-us/roofing-materials/residential-roofing-materials/residential-roll-roofing-products/liberty-roll-roofing "LIBERTY Roll Roofing System Products"

[A-S28]: https://www.gaf.com/en-us/roofing-materials/residential-roofing-materials/residential-roll-roofing/liberty-sbs-self-adhering-cap-sheet "LIBERTY Self-Adhering Cap Sheet"

[A-S29]: https://www.gaf.com/en-us/document-library/documents/data-sheets/liberty-sbs-self-adhering-cap-sheet-sell-sheet-reslb117.pdf "LIBERTY Self-Adhering Cap Sheet sell sheet RESLB117"
