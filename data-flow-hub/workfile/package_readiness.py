from release_tools import package
package('V1.11.A1','''# V1.11.A1 — Processing Readiness

Amends V1.11.0 and includes Compare Runs (V1.10.0) and Archive Retailers (V1.11.0). Client Setup Status now uses server-side saved-setup validation and sample schema checks, with expandable actionable issues and warnings. States are Archived, Needs attention, Needs sample check, or Ready for preprocessing. Data Streams retailer choices show the same readiness status.

Readiness validates retailer settings and executable rule configuration, then checks fields, condition fields, date formats and rename sequence against the saved sample when present. It does not require all three rule components or registered stores to call executable processing ready: empty rules and missing store registrations are explicit warnings. Reference-only rules remain blocked. Missing sample is explained, and users may instead check an actual batch in Data Streams. Archived retailers require restoration. The label Ready for preprocessing refers only to saved setup/sample schema; the actual file must pass preprocessing and may still fail data validation during execution.

Checks are read-only and create no jobs/configuration versions. Save and listing responses include consistent readiness/archive metadata. Each requested change has its own folder, changelog and GitHub commit. The single outputs/V1.3.A1.bat launcher switches to V1.11.A1 after all release verification is complete, at http://127.0.0.1:5001/.

Databases, uploaded samples, personal configuration, installed dependencies and generated build output are excluded from GitHub. Local SQLite data is preserved.
''','Production Vite build and 98 backend tests passed. Readiness tests cover missing sample, valid sample with optional components/stores, schema mismatch, unsupported references, archived/restored states and explicit parse-only warnings. Comparison, archive, failure-detail and existing tests passed. Interactive browser verification was not performed.\n',launcher=True)
