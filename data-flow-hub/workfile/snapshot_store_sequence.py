from pathlib import Path
import os,json
root=Path('outputs/V1.4.A2')
(root/'CHANGELOG_V1.4.A2.md').write_text('''# V1.4.A2 — Global MY6 storecode sequence

Amends V1.4.A1. SUITE storecodes now use MY6 followed by exactly seven zero-padded digits, starting at MY60000001. One persistent sequence serves all retailers: a new store in B can receive MY60000021, the next in A MY60000022, and the next in B MY60000023.

Allocations and retailer saves share a SQLite BEGIN IMMEDIATE transaction. A global registry enforces unique store identities, codes and sequence numbers. Simultaneous saves receive consecutive distinct numbers; failed saves roll back their allocation. Edits do not allocate new numbers, removing a store does not release its code, and restart/reinitialization preserves the counter. The allocator fails clearly at 9,999,999 instead of wrapping or extending the digit width.

At startup, existing valid MY6 codes are registered first and retained. UUID-style or missing storecodes are converted in retailer insertion order and existing store-array order, above the highest registered number. The registry retains each previous code as an internal migration reference. Migration is transactional and idempotent; duplicate existing MY6 codes are rejected rather than silently reassigned. User-provided codes remain ignored on ordinary store saves.

Updates the existing single V1.3.A1.bat launcher to start V1.4.A2 on port 5001. Local databases are backed up consistently and excluded from GitHub snapshots.
''',encoding='utf-8')
(root/'README.md').write_text('''# DataFlow V1.4.A2

Close the previous server window and open the same V1.3.A1.bat launcher. It now opens V1.4.A2 at http://127.0.0.1:5001/. Keep its window open. Fresh checkouts: run Setup_Windows.bat and Start_V1.4.A2.bat.

SUITE Storecode is automatically assigned on Save Store, using MY6 plus seven digits. The first new database starts at MY60000001. All retailers share the same counter: B → MY60000021, A → MY60000022, B → MY60000023. It never resets per retailer.

The code is read-only and remains fixed through store edits and retailer-key changes. Failed saves do not consume numbers; removed stores' numbers are not reused. The counter persists across restarts. The seven-digit limit is 9,999,999 stores allocated.

Existing UUID-style or missing codes convert to MY6 codes at first startup. Already-valid MY6 codes remain unchanged, and new allocations continue above the highest registered number. Previous codes are retained internally in store_code_registry. The previous release database remains available in its original version folder.

All Store Table Management, Rules Configuration and Data Streams features remain included.
''',encoding='utf-8')
(root/'VALIDATION.md').write_text('''# V1.4.A2 validation

Production React/Vite/Tailwind build passed. All 51 backend tests passed across the existing app, retailer/store management, rule configuration and batch jobs, plus eight new global-sequence checks. These cover interleaved retailers, stable edits and no number reuse, rollback on failed saves, five simultaneous allocations, legacy-code migration with existing MY6 values, exhaustion at the seven-digit limit, restart persistence and rejection of duplicate imported codes.

Live browser interaction is not part of these checks. Storecode generation and persistence were verified through the API and SQLite transactions.
''',encoding='utf-8')
entries=[]
for folder,dirs,files in os.walk(root):
 dirs[:]=[d for d in dirs if d not in {'node_modules','__pycache__','dist','.venv','.git','sample_data'}]
 for name in files:
  p=Path(folder)/name
  if p.suffix not in {'.py','.sql','.txt','.jsx','.js','.css','.html','.json','.md','.bat'} and name not in {'.gitignore','LICENSE'}:continue
  if name=='app-config.json' or name.startswith('LOCAL_') or '.timestamp-' in name:continue
  entries.append(dict(path='versions/V1.4.A2/'+p.relative_to(root).as_posix(),mode='100644',type='blob',content=p.read_text(encoding='utf-8-sig')))
entries.append(dict(path='versions/V1.3.A1/V1.3.A1.bat',mode='100644',type='blob',content=Path('outputs/V1.3.A1.bat').read_text()))
entries.append(dict(path='README.md',mode='100644',type='blob',content='''# DataFlow version history

Latest amendment: [V1.4.A2 — Global MY6 storecode sequence](versions/V1.4.A2/README.md).

Use the single [V1.3.A1.bat launcher](versions/V1.3.A1/V1.3.A1.bat), updated to open V1.4.A2. Keep version folders beside one another.

- V1.1.0: cleaning logs and exports.
- V1.2.0: retailer setup and ordered rules.
- V1.2.A1: batch audits, retries and replacements.
- V1.3.0: ordered rules table and conditions.
- V1.3.A1: single localhost launcher.
- V1.3.A2: compact Data Streams action icons.
- V1.4.0: component rule popups and execution codes.
- V1.4.A1: store edit page and generated storecodes.
- [V1.4.A2](versions/V1.4.A2/CHANGELOG_V1.4.A2.md): persistent global MY6 plus seven-digit sequence, transactional allocation and legacy-code migration.

Source snapshots exclude databases, uploads, credentials and installed dependencies.
'''))
Path('work/sequence_manifest.json').write_text(json.dumps(entries),encoding='utf-8')
print(len(entries),'source entries prepared')
