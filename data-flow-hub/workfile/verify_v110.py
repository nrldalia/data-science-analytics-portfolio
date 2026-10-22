import os,sys,io,csv
from pathlib import Path
root=Path(__file__).resolve().parent.parent
os.environ['DATAFLOW_DB']=str(root/'work/verify_v110.db')
sys.path.insert(0,str(root/'outputs/DataFlow_V1.1.0/script'))
import app
c=app.app.test_client()
source='sku,sales\n'+ '\n'.join(f' item{i} ,invalid' for i in range(31))
r=c.post('/api/v1/upload-and-clean',data={'file':(io.BytesIO(source.encode()),'verify.csv'),'rules':'{"numericFields":["sales"]}'})
assert r.status_code==200,r.data
d=r.get_json();rid=d['runId']
assert len(d['rawSample'])==25 and len(d['cleanedSample'])==25
assert len(d['transformationTrace'])+len(d['issues'])==62
r=c.get(f'/api/v1/runs/{rid}/log');assert r.status_code==200
assert len(list(csv.DictReader(io.StringIO(r.data.decode('utf-8-sig')))))==62
r=c.get(f'/api/v1/runs/{rid}/print');assert r.status_code==200 and r.data.count(b'<tr>')==63
assert c.post('/api/v1/ai-assist',json={'consent':True}).status_code==403
assert c.get('/').status_code==200
print('V1.1.0 verified: 25-row previews, 62-entry full CSV and print logs, dormant analysis, app homepage.')
