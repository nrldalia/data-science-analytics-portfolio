from pathlib import Path
import os,json
root=Path(__file__).resolve().parent.parent;release=root/'outputs/V1.9.0'
notes='''# V1.9.0 — Preprocessing checks before batch execution

Enhances V1.8.0. New batch and reprocessing forms first run Check Preprocessing. Results show file size, parsed row count, detected fields, blocking issues with rule sequence/name/code/actionable details, and nonblocking warnings. Once the check passes, the action becomes Start Job or Start Reprocessing. Reset Check allows another check; changing the file, retailer, period or Store ID override clears the previous report.

Checks cover parseable nonempty input, valid ISO week, saved retailer, rule settings and identities, unsupported reference-only operations, rule/condition fields in sequence, rename collisions, date-format directives and explicit Store ID overrides. Rename schema tracking accounts for unconditional renames; conditional renames have a warning because affected rows depend on data. No rules, missing store registrations and ambiguous automatic Store ID detection are warnings.

Checks are read-only and create no batch/job/configuration version. A blocked check is not a failed execution run. Data findings are not executed during preprocessing: invalid values may still fail validation during the job and produce its own cancelled/error-code row. This check does not guarantee successful processing.

The backend checks every launch, including direct API callers. The UI sends the checked configuration hash; later setup changes reject launch and require another check. Accepted runs snapshot check time, configuration hash, source SHA-256 and warnings alongside their pinned configuration version. Job creation and configuration capture use the latest checked setup in a transaction. No raw/cleaned data is added to execution audits.

Use the same outputs/V1.3.A1.bat launcher. Close the old server window and reopen it for V1.9.0 at http://127.0.0.1:5001/.

Local data is copied through SQLite backup. Databases, uploads, personal configuration, dependencies and build output are excluded from GitHub.
'''
for name in ['README.md','CHANGELOG_V1.9.0.md']:(release/name).write_text(notes,encoding='utf-8')
(release/'VALIDATION.md').write_text('Production Vite build and backend tests passed. Preprocessing checks cover read-only valid reports, confirmation receipt capture, multiple missing/condition/reference issues, rename sequence, invalid settings, stale-configuration rejection, malformed-file blocking and later data-failure execution. Existing batch tests reflect configuration/parse failures blocked before launch. Interactive browser verification was not performed.\n',encoding='utf-8')
entries=[]
for current,dirs,files in os.walk(release):
 dirs[:]=[d for d in dirs if d not in {'node_modules','__pycache__','dist','.venv','.git','sample_data'}]
 for name in files:
  p=Path(current)/name
  if name=='app-config.json' or name.startswith(('LOCAL_','.timestamp-')):continue
  if p.suffix not in {'.py','.sql','.txt','.jsx','.js','.css','.html','.json','.md','.bat'} and name not in {'.gitignore','LICENSE'}:continue
  entries.append(dict(path='versions/V1.9.0/'+p.relative_to(release).as_posix(),mode='100644',type='blob',content=p.read_text(encoding='utf-8-sig')))
entries.extend([dict(path='versions/V1.3.A1/V1.3.A1.bat',mode='100644',type='blob',content=(root/'outputs/V1.3.A1.bat').read_text(encoding='utf-8-sig')),dict(path='README.md',mode='100644',type='blob',content=notes)])
(root/'work/preprocessing_manifest.json').write_text(json.dumps(entries,ensure_ascii=False),encoding='utf-8')
print(f'Prepared {len(entries)} source files')
