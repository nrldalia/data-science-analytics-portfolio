import io,os,sys,time,sqlite3
from pathlib import Path

if __name__=='__main__':
    root=Path(__file__).resolve().parent.parent
    sys.path.insert(0,str(root/'outputs/V1.2.A1/script'))
    os.environ['DATAFLOW_DB']=str(root/'work/production_worker_smoke.db')
    import app
    c=app.app.test_client()
    app.app.config['BATCH_TIMEOUT_SECONDS']=60
    retailer=c.post('/api/v1/retailers',json={'name':'Worker Smoke Test','key':'WORKER_'+str(int(time.time())),'senderEmail':'internal@example.com','retailerEmail':'','serviceType':'SM','stores':[],'pipeline':[{'id':'trim','name':'Trim SKU','field':'sku','operation':'trim','category':'Cleaning'}],'sectionOrder':['Cleaning','Transformation','Validation']}).get_json()['retailer']['id']
    def submit(period):
        r=c.post('/api/v1/batches',data={'file':(io.BytesIO(b'sku\n worker \n'),'worker.csv'),'retailerId':retailer,'period':period})
        assert r.status_code==202,r.data
        return r.get_json()['attemptId']
    def wait(aid,limit):
        deadline=time.monotonic()+limit
        while time.monotonic()<deadline:
            d=c.get(f'/api/v1/batches/{aid}/status').get_json()
            if not d['processing']:return d['job']
            time.sleep(.1)
        raise AssertionError('Worker did not finish in time.')
    aid=submit('2026-W41');job=wait(aid,60)
    assert job['status']=='Completed',job
    audit=c.get(f'/api/v1/batches/{aid}/audit').get_json()
    assert len(audit['entries'])==2 and all(e['result']=='Successful' for e in audit['entries']),audit
    app.app.config['BATCH_TIMEOUT_SECONDS']=.01
    timed=wait(submit('2026-W42'),5)
    assert timed['status']=='Cancelled Job' and 'JOB_TIMEOUT' in timed['errorCodes'],timed
    print('Real Windows worker checks passed: subprocess parsing, rule execution, timing audit, and automatic timeout cancellation.')
