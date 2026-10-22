"""Bounded linked-input execution, sample walkthroughs and output column selection."""
import copy,json,math
from collections import defaultdict
from pathlib import PurePosixPath
JOIN_TYPES=['Inner','Left','Right','Full Outer','Cross']
MAX_ROWS=100000

def validate_special(rule):
    op=rule.get('operation')
    if rule.get('condition'):raise ValueError('Link Files and KPI checks apply to the complete dataset, without a row condition.')
    if op=='join':
        if rule.get('category')!='Link Files' or rule.get('joinType') not in JOIN_TYPES:raise ValueError('Choose a supported Link Files join.')
        for key in ['leftInputId','rightInputId']:
            if not isinstance(rule.get(key),str) or not rule[key]:raise ValueError('Select both linked inputs.')
        if rule['leftInputId']==rule['rightInputId']:raise ValueError('Select different linked inputs.')
        if rule['joinType']!='Cross':
            for key in ['leftField','rightField']:
                if not isinstance(rule.get(key),str) or not rule[key].strip():raise ValueError('Select both matching columns.')
        prefix=rule.get('rightPrefix','right_')
        if not isinstance(prefix,str) or not prefix or len(prefix)>50:raise ValueError('Enter a right-column prefix (1–50 characters).')
    elif op=='kpi':
        if rule.get('category')!='KPI':raise ValueError('Choose the KPI component.')
        from kpi_records import validate_kpi
        validate_kpi(rule.get('kpi'))
    else:raise ValueError('Unsupported workflow rule.')

def validate_output(config):
    mapping=config.get('columnMapping',[])
    if not isinstance(mapping,list) or len(mapping)>1000:raise ValueError('Use at most 1,000 mapped columns.')
    names=set();sources=set()
    for row in mapping:
        if not isinstance(row,dict) or not isinstance(row.get('source'),str) or not row['source'].strip() or not isinstance(row.get('name'),str) or not row['name'].strip() or max(len(row['source']),len(row['name']))>500:raise ValueError('Each mapped column requires a source and output name.')
        if row['source'] in sources or row['name'] in names:raise ValueError('Column sources and output names must be unique.')
        sources.add(row['source']);names.add(row['name'])
    analytics=config.get('analyticsColumns',[])
    if not isinstance(analytics,list) or len(analytics)>1000 or any(not isinstance(c,str) or not c.strip() or len(c)>500 for c in analytics) or len(set(analytics))!=len(analytics):raise ValueError('Select distinct analytics columns.')
    if mapping and any(c not in names for c in analytics):raise ValueError('Analytics columns must be included in Column Mapping.')
    profiles={p['id'] for p in config.get('inputFiles',[])}
    primary=config.get('primaryInputId','')
    if primary and primary not in profiles:raise ValueError('Choose a saved primary input.')
    if any(r.get('operation')=='join' for r in config.get('pipeline',[])) and not primary:raise ValueError('Select a primary input for linked processing.')
    linked=False;kpi_seen=False
    for rule in config.get('pipeline',[]):
        if kpi_seen:raise ValueError('Place the KPI check last, after other rules.')
        if rule.get('stage')=='Layout' and not linked:raise ValueError('Move Layout Rules after Link Files.')
        if rule.get('operation')=='kpi':kpi_seen=True
        if rule.get('operation')=='kpi' and rule.get('inputFileId') and next((p.get('purpose') for p in config.get('inputFiles',[]) if p['id']==rule['inputFileId']),None)!='Transaction':raise ValueError('KPI checks require a Transaction input.')
        if rule.get('inputFileId') and rule['inputFileId'] not in profiles:raise ValueError('A rule refers to a removed input file.')
        if rule.get('operation')=='join':
            linked=True
            if rule['rightInputId'] not in profiles or rule['leftInputId'] not in profiles|{'current'}:raise ValueError('Link Files refers to a removed input file.')
    return config

def schema_issues(state,config):
    datasets={pid:set(columns(rows)) for pid,rows in state['datasets'].items()};current=set(columns(state['current']));linked=False;issues=[]
    for seq,rule in enumerate(config['pipeline'],1):
        op=rule['operation'];pid=rule.get('inputFileId') if rule.get('stage')!='Layout' else None
        target=datasets.get(pid,set()) if pid else current
        try:
            if op=='join':
                left=current if rule['leftInputId']=='current' else datasets[rule['leftInputId']];right=datasets[rule['rightInputId']]
                if rule['joinType']!='Cross' and (rule['leftField'] not in left or rule['rightField'] not in right):raise ValueError('Link matching field is unavailable at this sequence.')
                names={(rule.get('rightPrefix','right_')+c if c in left else c) for c in right}
                if len(names|left)!=len(right)+len(left):raise ValueError('Linked output names collide; change the right prefix.')
                current=left|names;linked=True
            elif op=='kpi':continue
            else:
                if rule.get('stage')=='Layout' and not linked:raise ValueError('Layout requires an earlier link.')
                if rule['field'] not in target:raise ValueError('Rule field is unavailable in its selected input at this sequence.')
                if rule.get('condition') and rule['condition']['field'] not in target:raise ValueError('Condition field is unavailable at this sequence.')
                if op=='rename':
                    if rule['target']!=rule['field'] and rule['target'] in target:raise ValueError('Rename target already exists.')
                    if not rule.get('condition'):target.discard(rule['field'])
                    target.add(rule['target'])
                if pid==state['primary'] and not linked:current=set(target)
                if not pid and not linked and state['primary'] in datasets:datasets[state['primary']]=set(current)
        except (ValueError,KeyError) as exc:issues.append({'code':'WORKFLOW_SCHEMA_ERROR','message':str(exc),'sequence':seq,'ruleName':rule.get('name',''),'field':rule.get('field','')})
    if any(m['source'] not in current for m in config.get('columnMapping',[])):issues.append({'code':'OUTPUT_MAPPING_ERROR','message':'A mapped source is unavailable after the rules.','sequence':None,'ruleName':'Column Mapping','field':''})
    return issues

def required_inputs(pipeline,primary):
    ids={primary} if primary else set()
    for rule in pipeline:
        if rule.get('inputFileId'):ids.add(rule['inputFileId'])
        if rule.get('operation')=='join':ids.update([rule['rightInputId'],rule['leftInputId']])
    ids.discard('current');return ids

def sample_state(db,rid,config,primary):
    from input_file_io import parse_hash
    profiles={p['id']:p for p in config.get('inputFiles',[])}
    datasets={}
    for pid in required_inputs(config['pipeline'],primary):
        p=profiles.get(pid)
        if not p:raise ValueError('Select a saved primary input and valid linked inputs.')
        row=db.execute('SELECT * FROM input_file_samples WHERE retailer_id=? AND input_id=?',(rid,pid)).fetchone()
        if not row or row['settings_hash']!=parse_hash(p):raise ValueError(f'Upload a current sample for {p["filename"]}.')
        datasets[pid]=json.loads(row['records'])
    if primary not in datasets:raise ValueError('Choose the primary input sample.')
    return {'datasets':datasets,'primary':primary,'current':copy.deepcopy(datasets[primary]),'linked':False}

def launch_state(rid,config,primary,records):
    from input_files import load_profile,scoped_files,bounded_read
    from input_file_io import read_records
    from database import get_db_connection
    datasets={primary:records};inputs=[]
    for pid in sorted(required_inputs(config['pipeline'],primary)-{primary}):
        with get_db_connection() as db:_,profile,password=load_profile(db,rid,pid)
        files=scoped_files(profile)
        if len(files)!=1:raise ValueError(f'Linked input {profile["filename"]} needs exactly one matching saved-path file.')
        source=bounded_read(files[0]);datasets[pid]=read_records(source,files[0].name,profile,password)
        from hashlib import sha256
        inputs.append({'id':pid,'filename':files[0].name,'rowsReceived':len(datasets[pid]),'fileSizeBytes':len(source),'sha256':sha256(source).hexdigest()})
    return {'datasets':datasets,'primary':primary,'current':copy.deepcopy(records),'linked':False},inputs

def columns(rows):return list(dict.fromkeys(k for row in rows for k in row))

def join_records(left,right,rule):
    lc=columns(left);rc=columns(right);kind=rule['joinType'];lf=rule.get('leftField');rf=rule.get('rightField')
    if kind!='Cross' and (lf not in lc or rf not in rc):raise ValueError('Link matching field does not exist at this step.')
    names={c:(rule.get('rightPrefix','right_')+c if c in lc else c) for c in rc}
    if len(set(names.values())|set(lc))!=len(names)+len(lc):raise ValueError('Linked column names collide. Change the right-column prefix.')
    result=[];matched=set();index=defaultdict(list)
    def key(value):
        if value is None or str(value).strip()=='':return None
        return str(value).strip()
    for i,row in enumerate(right):
        k=key(row.get(rf))
        if k is not None:index[k].append((i,row))
    def emit(a,b):
        if len(result)>=MAX_ROWS:raise ValueError('Linked output exceeds 100,000 rows. Narrow the join or inputs.')
        result.append({**{c:(a or {}).get(c) for c in lc},**{names[c]:(b or {}).get(c) for c in rc}})
    for a in left:
        matches=list(enumerate(right)) if kind=='Cross' else index.get(key(a.get(lf)),[])
        for i,b in matches:emit(a,b);matched.add(i)
        if not matches and kind in ['Left','Full Outer']:emit(a,None)
    if kind in ['Right','Full Outer']:
        for i,b in enumerate(right):
            if i not in matched:emit(None,b)
    return result

def step(state,rule):
    from retailer_setup import apply_pipeline
    state=copy.deepcopy(state);op=rule['operation'];before=state['current'][:25]
    if op=='join':
        left=state['current'] if rule['leftInputId']=='current' else state['datasets'][rule['leftInputId']]
        before=left[:25];state['current']=join_records(left,state['datasets'][rule['rightInputId']],rule);state['linked']=True
        return {'state':state,'output':state['current'],'issueCount':0,'changedCells':0,'before':before,'after':state['current'][:25],'issues':[]}
    if op=='kpi':return {'state':state,'output':state['current'],'issueCount':0,'changedCells':0,'before':before,'after':before,'issues':[]}
    if rule.get('stage')=='Layout' and not state['linked']:raise ValueError('Layout Rules require a successful Link Files rule earlier in the sequence.')
    pid=rule.get('inputFileId') if rule.get('stage')!='Layout' else None
    target=state['datasets'].get(pid) if pid else state['current']
    if target is None:raise ValueError('Rule input file is unavailable.')
    if not target:return {'state':state,'output':state['current'],'issueCount':0,'changedCells':0,'before':[],'after':[],'issues':[]}
    output,steps,issues,trace=apply_pipeline(target,[rule])
    if pid:state['datasets'][pid]=output
    if not pid or (pid==state['primary'] and not state['linked']):state['current']=output
    if not pid and not state['linked'] and state['primary'] in state['datasets']:state['datasets'][state['primary']]=output
    return {'state':state,'output':state['current'],'issueCount':len(issues),'changedCells':len(trace),'before':steps[0]['before'],'after':steps[0]['after'],'issues':issues}

def mapped(records,mapping,analytics):
    available=set(columns(records))
    if records and any(row['source'] not in available for row in mapping):raise ValueError('A mapped column does not exist after the rules.')
    output=[{m['name']:row.get(m['source']) for m in mapping} for row in records] if mapping else records
    final={m['name'] for m in mapping} if mapping else available
    if records and any(c not in final for c in analytics):raise ValueError('An analytics column does not exist in the final output.')
    return output

def walkthrough(state,config):
    from retailer_setup import validate_pipeline
    validate_pipeline(config['pipeline']);validate_output(config)
    problems=schema_issues(state,config)
    if problems:raise ValueError(problems[0]['message'])
    original=state['current'][:25];steps=[];issues=[]
    for seq,rule in enumerate(config['pipeline'],1):
        result=step(state,rule);state=result['state'];issues.extend(result['issues'])
        steps.append({'id':rule['id'],'sequence':seq,'category':rule['category'],'name':rule['name'],'before':result['before'],'after':result['after'],'issues':result['issues'],'changedCells':result['changedCells'],'totalRows':len(state['current'])})
    output=mapped(state['current'],config.get('columnMapping',[]),config.get('analyticsColumns',[]))
    if config.get('columnMapping'):steps.append({'id':'mapping','sequence':len(steps)+1,'category':'Column Mapping','name':'Column Mapping','before':state['current'][:25],'after':output[:25],'issues':[],'changedCells':0,'totalRows':len(output)})
    return output,{'success':True,'original':original,'final':output[:25],'steps':steps,'sections':[],'issues':issues,'totalRows':len(output),'changedCells':sum(s['changedCells'] for s in steps),'issueRows':len({i['row'] for i in issues}),'columns':columns(output),'analyticsColumns':config.get('analyticsColumns',[])}

def execute_state(state,rule,queue):
    try:queue.put(step(state,rule))
    except (ValueError,KeyError,TypeError) as exc:queue.put({'errorCode':'LINK_OR_LAYOUT_ERROR','message':str(exc)})
    except Exception:queue.put({'errorCode':'RULE_EXECUTION_ERROR','message':'Linked workflow execution failed.'})
