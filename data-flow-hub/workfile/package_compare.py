from release_tools import package
package('V1.10.0','''# V1.10.0 — Compare Runs

Enhances V1.9.A1. Data Streams has Compare Runs with baseline and comparison selectors for retained runs of the same retailer. Side-by-side metrics cover received/cleaned rows, stores, New/Missing Store counts and IDs, file bytes, duration, status, configuration versions, failure details and error codes. Changes are comparison minus baseline; missing historical or cancelled metrics remain unavailable. Saved rule additions, removals, settings changes and sequence movements are identified using the captured run pipelines. Comparisons are read-only and contain no source or cleaned data previews.

Separate release folder and GitHub commit. The shared localhost launcher is intentionally left unchanged until all three requested releases are finished. Databases, uploaded samples, personal configuration and dependencies are excluded from GitHub.
''','Production Vite build and 93 backend tests passed. Comparison tests verify counts, changed rules, unavailable cancelled metrics, same-retailer enforcement, missing/duplicate selections and no data values in responses. Interactive browser verification was not performed.\n')
