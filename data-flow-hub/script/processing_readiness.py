"""Configuration/sample readiness, independent of mandatory component labels."""
import copy,json
from retailer_setup import validate_retailer,validate_pipeline
from preprocessing import check_configuration

def readiness(db,rid,config):
    issues=[];warnings=[]
    note='Checks saved setup and sample fields only. The actual batch still needs preprocessing; valid sample values do not guarantee a successful job.'
    if config.get('archived'):
        return {'status':'Archived','ready':False,'issues':[{'message':'Restore this retailer before editing or processing.'}],'warnings':[], 'note':note}
    try:validate_retailer(copy.deepcopy(config))
    except (ValueError,TypeError,KeyError) as exc:issues.append({'code':'INVALID_SETUP','message':str(exc)})
    try:validate_pipeline(config.get('pipeline',[]))
    except (ValueError,TypeError,KeyError) as exc:issues.append({'code':'INVALID_RULES','message':str(exc)})
    profiles=config.get('inputFiles',[])
    if profiles:
        from input_file_io import parse_hash
        missing=False
        for profile in profiles:
            sample=db.execute('SELECT * FROM input_file_samples WHERE retailer_id=? AND input_id=?',(rid,profile['id'])).fetchone()
            label=f"{profile['purpose']} ({profile['filename']})"
            kpi_rule=next((r for r in config.get('pipeline',[]) if r.get('operation')=='kpi' and (not r.get('inputFileId') or r['inputFileId']==profile['id'])),None)
            if profile['purpose']=='Transaction' and kpi_rule and any(not kpi_rule.get('kpi',{}).get(key) for key in ['salesField','quantityField','storeField']):
                warnings.append(label+': select KPI Sales, Quantity and Store ID fields; otherwise the completed run requires manual review.')
            if not sample or sample['settings_hash']!=parse_hash(profile):
                missing=True;warnings.append(label+': upload a sample matching the current input settings.');continue
            if config.get('primaryInputId') and profile['id']!=config['primaryInputId'] and (config.get('workflowVersion')==1 or any(r.get('operation')=='join' for r in config.get('pipeline',[]))):continue
            report=check_configuration(config,json.loads(sample['records']),'2026-W01',sample['filename'],b'')
            issues.extend({**issue,'message':label+': '+issue['message']} for issue in report['issues'])
            warnings.extend(label+': '+warning for warning in report['warnings'])
        if not missing and (config.get('workflowVersion')==1 or any(r.get('operation')=='join' for r in config.get('pipeline',[]))):
            try:
                from file_workflow import sample_state,schema_issues
                primary=config.get('primaryInputId') or profiles[0]['id']
                issues.extend(schema_issues(sample_state(db,rid,config,primary),config))
            except (ValueError,KeyError) as exc:issues.append({'code':'WORKFLOW_SCHEMA_ERROR','message':str(exc)})
        return {'status':'Needs attention' if issues else 'Needs sample check' if missing else 'Ready for preprocessing',
            'ready':not issues and not missing,'issues':issues,'warnings':warnings,'note':note}
    sample=db.execute('SELECT filename,records FROM retailer_samples WHERE retailer_id=?',(rid,)).fetchone()
    if not issues and sample:
        records=json.loads(sample['records'])
        report=check_configuration(config,records,'2026-W01',sample['filename'],b'')
        issues.extend(report['issues']);warnings.extend(report['warnings'])
    elif not sample:
        warnings.append('Upload a sample to check rule fields and rename sequence, or check the actual batch in Data Streams.')
        if not config.get('pipeline'):warnings.append('No rules configured: processing will parse and record the input only.')
        if not config.get('stores'):warnings.append('No registered stores: received Store IDs will be flagged as new when available.')
    status='Needs attention' if issues else 'Ready for preprocessing' if sample else 'Needs sample check'
    return {'status':status,'ready':not issues and bool(sample),'issues':issues,'warnings':warnings,'note':note}
