"""Snapshot weekly KPI comparisons and explicit operator review."""
import json,math
from datetime import datetime,timedelta
from decimal import Decimal,DecimalException
from flask import request,jsonify
from database import get_db_connection, begin_write
DEFAULTS={'weeks':8,'storeLimit':30,'retailerLimit':30,'countLimit':40,'salesField':'','quantityField':'','storeField':''}
def validate_kpi(value):
    if value is None:value={}
    if not isinstance(value,dict):raise ValueError('Invalid KPI settings.')
    result=DEFAULTS|value
    if isinstance(result['weeks'],bool) or not isinstance(result['weeks'],int) or not 1<=result['weeks']<=52:raise ValueError('KPI weeks must be from 1 to 52.')
    for key in ['storeLimit','retailerLimit','countLimit']:
        if isinstance(result[key],bool) or not isinstance(result[key],(int,float)) or not math.isfinite(result[key]) or not 0<=result[key]<=1000:raise ValueError('KPI ranges must be finite percentages from 0 to 1000.')
    for key in ['salesField','quantityField','storeField']:
        if not isinstance(result[key],str) or len(result[key])>200:raise ValueError('Select valid KPI fields.')
        result[key]=result[key].strip()
    return {key:result[key] for key in DEFAULTS}
def totals(records,settings):
    sales=Decimal(0);quantity=Decimal(0);stores={};issues=[]
    missing=[key for key in ['salesField','quantityField','storeField'] if not settings[key]]
    if missing:return {'sales':None,'quantity':None,'rows':len(records),'stores':{},'issues':['Select Sales, Quantity and Store ID fields in Transaction input settings.']}
    invalid=0
    for row in records:
        try:
            amount=Decimal(str(row[settings['salesField']]).strip());units=Decimal(str(row[settings['quantityField']]).strip())
            store=str(row[settings['storeField']]).strip() if row[settings['storeField']] is not None else ''
            if not amount.is_finite() or not units.is_finite() or not store:raise ValueError()
            key=store.casefold();next_sales=sales+amount;next_quantity=quantity+units
            next_store=stores.get(key,{}).get('sales',Decimal(0))+amount
        except (KeyError,DecimalException,ValueError,TypeError):invalid+=1;continue
        sales=next_sales;quantity=next_quantity
        if key not in stores:stores[key]={'storeId':store,'sales':Decimal(0)}
        stores[key]['sales']=next_store
    if invalid:issues.append(f'{invalid} rows have missing or invalid KPI fields. Totals are unavailable until these are corrected.')
    try:
        numeric=[float(sales),float(quantity),*[float(s['sales']) for s in stores.values()]]
        if not all(math.isfinite(v) for v in numeric):raise ValueError()
    except (OverflowError,ValueError):issues.append('KPI totals exceed the supported numeric range.')
    if issues:return {'sales':None,'quantity':None,'rows':len(records),'stores':{},'issues':issues}
    return {'sales':float(sales),'quantity':float(quantity),'rows':len(records),
        'stores':{key:{'storeId':s['storeId'],'sales':float(s['sales'])} for key,s in stores.items()},'issues':[]}
def change(current,baseline):
    if current is None or baseline is None:return None
    if baseline==0:return 0.0 if current==0 else None
    result=float((Decimal(str(current))-Decimal(str(baseline)))/abs(Decimal(str(baseline)))*100)
    return result if math.isfinite(result) else None

def average(values):
    return float(sum((Decimal(str(v)) for v in values),Decimal(0))/len(values)) if values else None
def evaluate_kpi(db,rid,period,records,profile):
    if not profile or profile.get('purpose')!='Transaction':return None
    settings=validate_kpi(profile.get('kpi'));current=totals(records,settings)
    year,week=period.split('-W');start=datetime.fromisocalendar(int(year),int(week),1)
    periods=[(start-timedelta(weeks=i)).isocalendar() for i in range(1,settings['weeks']+1)]
    periods=[f'{p.year:04d}-W{p.week:02d}' for p in periods]
    history=[];missing=[]
    for prior in periods:
        candidates=db.execute("SELECT id,output FROM batch_jobs WHERE retailer_id=? AND period=? AND status IN ('Completed','Approved Job') AND json_extract(metrics,'$.inputFile.id')=? ORDER BY start_time DESC,rowid DESC",(rid,prior,profile['id'])).fetchall()
        chosen=None
        for row in candidates:
            if not row['output']:continue
            aggregate=totals(json.loads(row['output']),settings)
            if not aggregate['issues']:chosen={'jobId':row['id'],'period':prior,**aggregate};break
        if chosen:history.append(chosen)
        else:missing.append(prior)
    n=len(history);mean=lambda key:average([h[key] for h in history])
    retailer_base=mean('sales');count_base=mean('rows')
    retailer_percent=change(current['sales'],retailer_base);count_percent=change(current['rows'],count_base)
    flags=list(current['issues']);stores=[]
    if not n:flags.append('No eligible previous-week baseline. Check this first KPI run manually.')
    if not current['issues'] and n:
        keys=set(current['stores'])|{key for h in history for key in h['stores']}
        for key in sorted(keys):
            previous=[h['stores'].get(key,{}).get('sales',0) for h in history]
            baseline=average(previous);present=current['stores'].get(key)
            store_id=(present or next(h['stores'][key] for h in history if key in h['stores']))['storeId']
            amount=present['sales'] if present else 0;percent=change(amount,baseline)
            flagged=percent is None or abs(percent)>settings['storeLimit']
            reason='Nonzero sales against a zero store baseline.' if percent is None else 'Outside allowed store range.' if flagged else ''
            stores.append({'storeId':store_id,'sales':amount,'baselineSales':baseline,'percent':percent,'flagged':flagged,'reason':reason})
        if any(s['flagged'] for s in stores):flags.append('One or more stores are outside the allowed sales range or have a zero baseline.')
        if retailer_percent is None:flags.append('Retailer sales percentage is unavailable against a zero baseline.')
        elif abs(retailer_percent)>settings['retailerLimit']:flags.append('Retailer sales are outside the allowed range.')
        if count_percent is None:flags.append('Row-count percentage is unavailable against a zero baseline.')
        elif abs(count_percent)>settings['countLimit']:flags.append('Rows Count is outside the allowed range.')
    available=[s['percent'] for s in stores if s['percent'] is not None]
    return {'settings':settings,'sales':current['sales'],'quantity':current['quantity'],'rowsCount':current['rows'],
        'storePercent':average(available) if available and len(available)==len(stores) else None,
        'retailerPercent':retailer_percent,'countPercent':count_percent,'baselineSales':retailer_base,'baselineRows':count_base,
        'weeksUsed':n,'missingWeeks':missing,'baselineRuns':[{'jobId':h['jobId'],'period':h['period']} for h in history],
        'stores':stores,'flagged':bool(flags),'flags':flags,'review':None}
def public_record(row):
    metrics=json.loads(row['metrics'] or '{}')
    return {k:row[k] for k in ['id','retailer_id','retailer_name','period','filename','status','start_time']} | {
        'inputFile':metrics.get('inputFile'),'kpi':metrics.get('kpi'),'approvedAt':metrics.get('approvedAt')}
def register_kpi_routes(app,error):
    @app.route('/api/v1/kpi-records')
    def records():
        with get_db_connection() as db:
            rows=[public_record(r) for r in db.execute("SELECT * FROM batch_jobs WHERE json_extract(metrics,'$.inputFile.purpose')='Transaction' ORDER BY start_time DESC,rowid DESC")]
        return jsonify(success=True,records=rows)
    @app.route('/api/v1/batches/<jid>/kpi-review',methods=['POST'])
    def review(jid):
        body=request.get_json(silent=True)
        if not isinstance(body,dict) or body.get('checked') is not True or not isinstance(body.get('note'),str) or not body['note'].strip() or len(body['note'])>1000:return error('Confirm the manual check and enter a review note (up to 1,000 characters).')
        with get_db_connection() as db:
            begin_write(db);job=db.execute('SELECT * FROM batch_jobs WHERE id=?',(jid,)).fetchone()
            if not job:return error('Job not found.',404)
            metrics=json.loads(job['metrics'] or '{}');kpi=metrics.get('kpi')
            if job['status'] not in ['Completed','Completed with Interruption'] or not kpi or not kpi['flagged']:return error('Only a completed, flagged KPI run can be reviewed.',409)
            if kpi.get('review'):return error('KPI review is already recorded.',409)
            from batch_jobs import now
            stamp=now();kpi['review']={'checkedAt':stamp,'note':body['note'].strip()}
            audit=json.loads(job['audit'] or '[]');audit.append({'sequence':None,'ruleName':'Manual KPI review','category':'Action','attempt':1,'startTime':stamp,'endTime':stamp,'durationMs':0,'result':'Successful','errorCode':None,'message':body['note'].strip()})
            db.execute('UPDATE batch_jobs SET metrics=?,audit=? WHERE id=?',(json.dumps(metrics),json.dumps(audit),jid))
        return jsonify(success=True,review=kpi['review'])
