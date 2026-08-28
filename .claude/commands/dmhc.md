You are answering questions about DMHC (California Department of Managed Health Care) regulatory filings. The filings live in `docs/dmhc-cases/2026-HOSP-*` (hospital contract terminations) and `docs/dmhc-cases/2026-PROV-*` (provider/physician group terminations). Each directory is one case and contains extracted `.txt` files from the original PDFs.

## Key files per case directory
- `Details Tab.txt` — structured case metadata: plan name, termination cause, enrollee counts by county/product, alternate providers, services comparison
- `Communication w-Plan Tab.txt` — DMHC ↔ plan email thread
- `CommentLetter_*.txt` — DMHC comment letters requesting more info
- `ResponsetoCommentLetter_*.txt` — plan's responses
- Numbered `.txt` files (e.g. `1773703643526.txt`) — attachments (letters, notices, supporting docs)

## How to answer

**If the user names a specific case** (e.g. "HOSP-90", "2026-PROV-94"):
1. `ls docs/dmhc-cases/2026-HOSP-90/` to see all files
2. Read `Details Tab.txt` and `Communication w-Plan Tab.txt` first
3. Read any other `.txt` files relevant to the question
4. Answer directly from the text

**If the user asks a general or cross-case question** (e.g. "which cases involve Anthem?", "how many cases are hospital-initiated?"):
1. `grep -rl "Anthem" docs/dmhc-cases/` to find matching cases (adjust pattern to query)
2. Read the `Details Tab.txt` for each matching case
3. Synthesize across cases

**If the user asks to summarize all cases** or compare across the full corpus:
1. Read every `Details Tab.txt` file: `find docs/dmhc-cases -name "Details Tab.txt"`
2. Build a summary table or narrative from the structured fields

## Field vocabulary to know
- "Cause of Contract Termination" — typically "Hospital Initiated" or "Plan Initiated" or "Mutual"
- "Termination Notice Days" — how many days' notice was given
- "Enrollees Assigned\Unassigned" — whether enrollees are actively assigned to this provider
- "Timely Access Justification Required" — DMHC's access standard check
- "Evergreen" — whether the contract auto-renews
- "Date Contract Terminates" — `1/1/9999` means ongoing/unresolved at filing time

## Output style
Answer concisely. For cross-case queries, a markdown table is usually clearest. Always cite the case number (e.g. `2026-HOSP-90`) when referencing specific data. If a field says "Unanswered" in the source, note it rather than omitting it.

$ARGUMENTS
