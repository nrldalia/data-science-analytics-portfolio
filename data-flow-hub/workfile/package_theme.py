from release_tools import package
package('V1.14.A1','''# V1.14.A1 — Light and Dark Colours

Amends V1.14.0 with the supplied reference's purple accent, deep indigo/lavender dark surfaces and pale lavender/white light surfaces. The header has labelled Light and Dark buttons with selected state. A saved browser preference is restored on reload; the operating-system colour preference supplies the initial choice when no saved choice exists. Browser storage being unavailable does not prevent switching. The selected palette is applied before React renders, and native controls use the matching colour scheme.

Shared colour tokens cover Client, Retailer Setup, Input Files, Rules Configure, Column Mapping, Output Format, Data Streams, KPI Records, forms, table headers, borders and popups. Active sidebar navigation uses a solid purple highlight. Primary actions have white labels, and success/warning/failure colours remain distinct and readable in both modes. Visible keyboard focus and reduced-motion preferences are supported. The reference supplies colour direction; the existing DataFlow layout and functionality are retained.

Includes the V1.14.0 linked-input workflow, five join types, Layout Rules, explicit KPI checks, step-through previews, output mapping and analytics selections. Local retailer configurations, job data and passwords are preserved by SQLite backup. Browser theme choices are stored locally and are not published to GitHub.

Close the previous server window and reopen the single outputs/V1.3.A1.bat launcher. It opens V1.14.A1 at http://127.0.0.1:5001/. Use Light / Dark beside the version badge. Databases, samples, uploaded files, secrets, personal configuration, dependencies and generated builds remain excluded from GitHub.
''','''Production Vite build passed. Theme checks verified system preference fallback, saved-choice precedence, applying and restoring Light/Dark, matching native colour scheme and switching with browser storage disabled. Sixteen foreground/panel and primary-button contrast checks met at least 4.5:1. Eight API/served-frontend regression tests passed. Existing batch-processing behavior is unchanged; no new backend behavior was introduced. Interactive browser verification was not performed.
''',launcher=True)
