import json
from pathlib import Path

root = Path(__file__).resolve().parent.parent
release = root / 'outputs/V1.4.A3'
notes = '''# V1.4.A3 — Rule reference dropdowns

Added 496 selectable references derived from the supplied cleaning, transformation and validation document, including hashing and advanced algorithms. Dropdown labels contain rule names only. Choosing a rule prefills an editable example of fewer than ten words in Description.

References are grouped under Cleaning, Transformation and Validation. Existing executable rules and custom rules remain available. Exactly matching supported references use the existing execution engine. Other references show a Reference only label and can be saved for planning; preview, export and batch execution reject them with a clear message until an execution engine is implemented.

The component popup, individual rule rows, sequence controls, description editing and separate Condition editing remain available.

Use the existing outputs/V1.3.A1.bat launcher. Close the old server window and reopen that launcher to load V1.4.A3 at http://127.0.0.1:5001/.

The original reference document, databases, uploads, personal configuration and dependencies are excluded from GitHub.
'''
(release / 'CHANGELOG_V1.4.A3.md').write_text(notes, encoding='utf-8')
(release / 'VALIDATION.md').write_text('''# Validation

Production Vite build passed. Backend regression tests and reference catalog tests passed: catalog coverage, examples under ten words, persistent reference descriptions, mapped trim execution, and clear rejection of unsupported reference preview/export/execution.

Interactive browser verification was unavailable in this session. Restart the existing launcher to review the updated UI locally.
''', encoding='utf-8')
(release / 'README.md').write_text(notes, encoding='utf-8')
entries = []
for path in sorted(release.rglob('*')):
    rel = path.relative_to(release)
    if not path.is_file() or any(p in {'node_modules', '__pycache__', 'dist', '.venv', '.git', 'sample_data'} for p in rel.parts):
        continue
    if path.name == 'app-config.json' or path.name.startswith(('LOCAL_', '.timestamp-')):
        continue
    if path.suffix not in {'.py', '.sql', '.txt', '.jsx', '.js', '.css', '.html', '.json', '.md', '.bat'} and path.name not in {'.gitignore', 'LICENSE'}:
        continue
    entries.append({'path': 'versions/V1.4.A3/' + rel.as_posix(), 'mode': '100644', 'type': 'blob', 'content': path.read_text(encoding='utf-8-sig')})
entries.append({'path': 'versions/V1.3.A1/V1.3.A1.bat', 'mode': '100644', 'type': 'blob', 'content': (root / 'outputs/V1.3.A1.bat').read_text(encoding='utf-8-sig')})
entries.append({'path': 'README.md', 'mode': '100644', 'type': 'blob', 'content': notes})
(root / 'work/references_manifest.json').write_text(json.dumps(entries, ensure_ascii=False), encoding='utf-8')
print(f'Prepared {len(entries)} public source files')
