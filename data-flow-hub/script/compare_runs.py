"""Read-only comparisons of retained runs; never expose batch values."""
import json
from datetime import datetime
from flask import request,jsonify
from database import get_db_connection
from batch_metrics import public_metrics

def summary(row):
    metrics=public_metrics(json.loads(row['metrics'] or '{}'))
    duration=None
    if row['end_time']:
        duration=round((datetime.fromisoformat(row['end_time'])-datetime.fromisoformat(row['start_time'])).total_seconds(),3)
    return {k:row[k] for k in ['id','retailer_id','retailer_name','period','start_time','end_time','status','filename']} | {
        'metrics':metrics,'durationSeconds':duration,'errorCodes':json.loads(row['error_codes'] or '[]'),
        'rules':json.loads(row['pipeline'] or '[]')}

def register_compare_routes(app,error):
    @app.route('/api/v1/batches/compare')
    def compare_runs():
        left=request.args.get('left');right=request.args.get('right')
        if not left or not right or left==right:return error('Choose two different recorded runs.')
        with get_db_connection() as db:
            a=db.execute('SELECT * FROM batch_jobs WHERE id=?',(left,)).fetchone()
            b=db.execute('SELECT * FROM batch_jobs WHERE id=?',(right,)).fetchone()
        if not a or not b:return error('A selected run no longer exists.',404)
        if a['retailer_id']!=b['retailer_id']:return error('Compare runs from the same retailer.')
        a=summary(a);b=summary(b)
        deltas={}
        for key in ['rowsReceived','rowsAfterCleaning','storesReceived','storeTotalIncludingNew','fileSizeBytes']:
            x=a['metrics'].get(key);y=b['metrics'].get(key)
            deltas[key]=y-x if isinstance(x,(int,float)) and isinstance(y,(int,float)) else None
        for key in ['newStores','missingStores']:
            x=a['metrics'].get(key);y=b['metrics'].get(key)
            deltas[key]=len(y)-len(x) if isinstance(x,list) and isinstance(y,list) else None
        deltas['durationSeconds']=round(b['durationSeconds']-a['durationSeconds'],3) if a['durationSeconds'] is not None and b['durationSeconds'] is not None else None
        old={r['id']:(i,r) for i,r in enumerate(a['rules'],1)};new={r['id']:(i,r) for i,r in enumerate(b['rules'],1)}
        changes=[]
        for rid in dict.fromkeys([*old,*new]):
            x=old.get(rid);y=new.get(rid)
            if x==y:continue
            changes.append({'ruleId':rid,'ruleName':(y or x)[1].get('name',''),
                'change':'Added' if x is None else 'Removed' if y is None else 'Changed and moved' if x[1]!=y[1] and x[0]!=y[0] else 'Changed' if x[1]!=y[1] else 'Moved',
                'beforeSequence':x[0] if x else None,'afterSequence':y[0] if y else None})
        return jsonify(success=True,left=a,right=b,deltas=deltas,ruleChanges=changes)
