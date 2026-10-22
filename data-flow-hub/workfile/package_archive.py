from release_tools import package
package('V1.11.0','''# V1.11.0 — Archive Retailers

Enhances V1.10.0. Client supports bulk Archive and Restore, with separate active and archived views. Archive preserves setup, store identities/codes, retailer key, sample and all run/configuration history. Archive/restore events and timestamps are recorded in the database and available through archive-history API. Archived retailers are excluded from new-job choices; launch and reprocessing are blocked server-side. Restore permits processing again. Archived setup/sample changes and new-store approvals require restore, while existing audits and comparisons remain readable.

Bulk archive validates every selected retailer before changing any and rejects retailers with running jobs. Repeated archive/restore is idempotent. Existing Delete remains an explicit separate action. Archive does not release retailer keys or reuse store codes.

Separate release folder and GitHub commit. Shared localhost launcher remains unchanged until Processing Readiness is complete. Databases, samples, personal configuration and dependencies are excluded from GitHub.
''','Production Vite build and 95 backend tests passed. Archive tests verify preserved setup/sample/audit history, blocked launches/reprocessing/edits, preprocessing archive errors, restoration, timestamped events, active-job rejection and atomic/idempotent bulk actions. Interactive browser verification was not performed.\n')
