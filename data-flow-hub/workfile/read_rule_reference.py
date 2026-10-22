from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET
source=Path(r'C:\Users\nurul\Downloads\Data Cleaning, Transformation & Validation Reference.docx')
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
with ZipFile(source) as doc:
 tree=ET.fromstring(doc.read('word/document.xml'))
 lines=[''.join(p.itertext()) for p in []]
 lines=[''.join(t.text or '' for t in p.findall('.//w:t',ns)) for p in tree.findall('.//w:p',ns)]
text='\n'.join(line for line in lines if line.strip())
Path('work/rules_reference.txt').write_text(text,encoding='utf-8')
print(text)
