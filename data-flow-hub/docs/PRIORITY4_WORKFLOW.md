# Priority 4: processing and operational trends

This development cycle extends the existing batch workflow. It does not replace
saved retailer setups, rewrite historical source files, or automatically correct
records. User data and earlier processing runs remain intact.

## Existing capabilities to retain

- Preprocessing checks validate the reporting ISO week, input columns, selected
  input profile, ordered rules and linked input configuration before launch.
- A configuration hash detects changes between checking and launching.
- Each batch run has its own identity, source file, reporting period, input
  profile and captured configuration version. Reprocessing creates another run.
- Processing snapshots the expected active-store roster and registered IDs.
- Rule execution already supports bounded retries, cancellation and a deadline.
- Transaction KPI snapshots, manual KPI review, store review and job approval
  are separate actions.
- The original cancelled-run audit endpoint has legacy semantics; new failure
  evidence must not silently change old API guarantees.

## Operator flow and acceptance criteria

1. **Select and check.** Choose a saved retailer, input profile, business ISO week
   and file. Explain blocking errors separately from warnings. No run or data
   changes occur merely from viewing a check.
2. **Process.** Show the current stage/rule, attempt count, elapsed time and
   completed work. Do not imply a predictive time estimate or row-level
   completion percentage when the worker has not measured it.
3. **Investigate.** Keep bounded evidence explaining failure or interruption,
   including rule/field, error code, affected-row count and row references where
   available. General job lists must not expose cell contents or secrets.
4. **Reconcile.** Compare distinct received store IDs against the roster captured
   at launch. Unknown stores and inactive known stores must not inflate active
   store coverage. Missing/ambiguous store mapping is unavailable, never zero.
5. **Review.** An operator note records a review; it does not modify the source,
   invent a correction, dismiss an unrecoverable validation failure or approve a
   cancelled job. Keep KPI review, new-store registration and job approval distinct.
6. **Retry safely.** Reprocessing uses the retained original source and current
   explicitly saved configuration, after another preprocessing check. Preserve
   the original run and its configuration/evidence. Prevent conflicting active
   launches, and identify lineage where captured rather than guessing history.
7. **Export.** Exports identify the run, reporting period, configuration and source
   fingerprint. Successful processed output, reconciliation and bounded execution
   evidence must have clear labels; failed runs must not masquerade as successful
   output. Spreadsheet CSV cells must be safe from formula interpretation.

## Weekly operational trends

Use the **business ISO week** for the horizontal axis and store receipt/processing
and approval timestamps separately. Reporting a historical week today must not
move its data into today's business week.

A published result is one explicitly approved run per retailer, input-profile
scope and business week. When another eligible run is approved in the same scope,
use the documented latest-approval policy for the published trend while retaining
all earlier runs and their versions. Repeated attempts must not be summed as
additional business submissions. Unapproved completed runs are provisional and
must not silently enter approved totals.

Missing weeks are gaps with unavailable values, not zeroes. An incomplete or
unapproved week is provisional, not a completed period with zero activity.
Calculations must expose the chosen source run and calculation version so that a
revision is explainable. Current store edits must not rewrite historical
coverage denominators.

Recommended initial measures and their required evidence:

| Measure | Definition and boundary |
| --- | --- |
| Expected-store coverage | Expected active IDs received / expected active IDs, from the selected run's captured roster and missing-store reconciliation. |
| Missing stores | Expected active IDs absent from that run. Unknown and inactive IDs are separate categories. |
| Processed rows | Captured final output row count; unknown historical counts remain unavailable. |
| Failure/reprocessing | Attempt and lineage counts when reliably captured. Do not infer a logical-submission denominator solely from filenames. |
| Duration | Observed elapsed processing duration. Historical cancelled runs may lack end times and must not get invented durations. |
| Data quality | Distinct affected input rows / rows checked only when row identities and scope are captured. Retry issue counts must not be added as separate affected rows. |
| On-time coverage | Requires a saved period deadline and receipt time policy. A business period alone is insufficient; keep unavailable until these are defined. |

Rolling comparisons must state their window and data availability. Keep retailers
and input profiles distinguishable; aggregate percentages using their available
numerators and denominators rather than an unweighted mean of store coverage.
Sales and like-for-like retail trends are separate from this initial operational
view; they require explicit sales/returns rules and appropriate sales fixtures.

## Verification checklist

- A valid run shows measured progress, completes and exposes its evidence.
- An invalid rule/file cannot become approved by adding a review note.
- Failed/restarted/cancelled processing retains the evidence actually captured,
  without inventing successful output or exposing raw values in global lists.
- Reprocessing preserves the original run/source and identifies its parent where
  recorded; a second active launch cannot overwrite or duplicate an attempt.
- One period with multiple approved attempts contributes once per input scope.
- Changing the current store roster leaves prior coverage unchanged.
- Unknown and inactive received IDs never produce coverage over 100 percent.
- Missing weeks, unavailable mapping and historical missing evidence remain null
  or explicitly unavailable; they are not plotted as zero.
- Period selection works across ISO-year boundaries.
- Exported figures match the run detail, reconciliation and trend source records.
- Approval/publication changes are serialized and can be traced to a run/version.

## Known boundaries

This is a local portfolio application, not a multi-user authenticated production
service. Do not imply a review note establishes a verified human identity. Deadline
SLAs, fully persistent distributed workers and trained anomaly models require
separate product decisions. UI progress must describe observed work rather than
promise these capabilities.
