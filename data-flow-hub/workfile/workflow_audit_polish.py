from pathlib import Path
root=Path(__file__).resolve().parent.parent/'outputs/V1.14.0'
p=root/'frontend-github/src/WorkflowRules.jsx';s=p.read_text(encoding='utf-8').replace('if(!pid||(pid===primary&&!linked))current=cols;','if(!pid||(pid===primary&&!linked))current=cols;if(!pid&&!linked&&primary)datasets[primary]=cols;');p.write_text(s,encoding='utf-8')
p=root/'script/batch_jobs.py';s=p.read_text(encoding='utf-8').replace("            else:mapping_error=False\n            selected=","            else:\n                mapping_error=False\n                if metrics.get('columnMapping'):\n                    stamp=now();audit.append({'sequence':len(pipeline)+1,'ruleName':'Column Mapping','category':'Column Mapping','attempt':1,'startTime':stamp,'endTime':stamp,'durationMs':0,'result':'Successful','executionCode':'909','errorCode':None,'message':f'{len(metrics[\"columnMapping\"])} output columns selected and ordered; {len(metrics.get(\"analyticsColumns\",[]))} analytics columns saved.'})\n            selected=")
s=s.replace("'sequence':None,'ruleName':'KPI checks','category':'KPI'","'sequence':next(i for i,r in enumerate(pipeline,1) if r['id']==selected['id']),'ruleId':selected['id'],'ruleName':selected.get('name','KPI checks'),'category':'KPI'")
p.write_text(s,encoding='utf-8')
print('Preserved pre-link changes and added mapping audit evidence.')
