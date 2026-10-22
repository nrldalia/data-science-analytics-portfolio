from pathlib import Path
import re
root=Path(__file__).resolve().parent
fragment=(root/'kpi-record-design.html').read_text(encoding='utf-8')
fragment=fragment.replace('#kpi-design-preview button{cursor:inherit}','')
(root/'kpi-record-design.html').write_text(fragment,encoding='utf-8')
assert '<!doctype' not in fragment.lower() and '<html' not in fragment.lower()
assert '\\"' not in fragment and '\\n' not in fragment
ids=re.findall(r'\bid="([^"]+)"',fragment)
assert len(ids)==len(set(ids))
script=re.search(r'<script>([\s\S]*?)</script>',fragment).group(1)
(root/'kpi_design_runtime.js').write_text(script,encoding='utf-8')
print(f'Fragment read-back passed; {len(ids)} unique elements; {len(fragment.encode())} bytes.')
