from pathlib import Path
p=Path('outputs/V1.5.0/script/batch_jobs.py');s=p.read_text()
s=s.replace('from retailer_setup import apply_pipeline, validate_pipeline','from retailer_setup import apply_pipeline, validate_pipeline, validate_retailer, assign_store_codes\nfrom batch_metrics import input_metrics, received_metrics, public_metrics, previous_period')
s=s.replace("'lastAttempt':decode(row['last_attempt'],None)","'metrics':public_metrics(decode(row['metrics'],{})), 'lastAttempt':decode(row['last_attempt'],None)")
marker='    def finalize(aid, status, output=None, audit=None, codes=None):'
s=s.replace(marker,"""    with get_db_connection() as db:
        for table in ['batch_jobs','batch_attempts']:
            if 'metrics' not in [r['name'] for r in db.execute(f'PRAGMA table_info({table})')]:
                db.execute(f'ALTER TABLE {table} ADD COLUMN metrics TEXT')

"""+marker)
s=s.replace("INSERT INTO batch_jobs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)","INSERT INTO batch_jobs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)")
s=s.replace("json.dumps(codes or []),None))","json.dumps(codes or []),None,attempt['metrics']))")
s=s.replace("        pipeline=decode(attempt['pipeline'],[])","""        metrics=decode(attempt['metrics'],{})
        received_metrics(metrics,records)
        pipeline=decode(attempt['pipeline'],[])
        # Cleaning count is the output at the last Cleaning step, before later transformations.
        metrics['rowsAfterCleaning']=len(records) if not any(r['category']=='Cleaning' for r in pipeline) else None
        with get_db_connection() as db:db.execute('UPDATE batch_attempts SET metrics=? WHERE id=?',(json.dumps(metrics),aid))""")
s=s.replace("                records=result['output'];break","""                records=result['output']
                if rule['category']=='Cleaning':
                    metrics['rowsAfterCleaning']=len(records)
                    with get_db_connection() as db:db.execute('UPDATE batch_attempts SET metrics=? WHERE id=?',(json.dumps(metrics),aid))
                break""")
s=s.replace('def launch(retailer_id,period,filename,source):',"def launch(retailer_id,period,filename,source,store_field=''):")
s=s.replace("            aid='BATCH-'", """            if not isinstance(store_field,str) or len(store_field)>200:return error('Store ID column must be at most 200 characters.')
            previous=db.execute("SELECT source FROM batch_jobs WHERE retailer_id=? AND period=? AND status!='Cancelled Job'",(retailer_id,previous_period(period))).fetchone()
            metrics=input_metrics(source,period,config.get('stores',[]),previous,store_field.strip())
            aid='BATCH-'""")
s=s.replace("INSERT INTO batch_attempts VALUES(?,?,?,?,?,?,?,?,?,?)","INSERT INTO batch_attempts VALUES(?,?,?,?,?,?,?,?,?,?,?)")
s=s.replace("json.dumps(pipeline),deadline,'{}'))","json.dumps(pipeline),deadline,'{}',json.dumps(metrics)))")
s=s.replace("file.filename,file.read())","file.filename,file.read(),request.form.get('storeIdField',''))")
s=s.replace("job['filename'],job['source'])","job['filename'],job['source'],decode(job['metrics'],{}).get('storeIdField',''))")
needle="            entries=decode(job['audit'],[])"
s=s.replace(needle,"""            metrics=decode(job['metrics'],{})
            retailer=db.execute('SELECT payload FROM retailer_configs WHERE id=?',(job['retailer_id'],)).fetchone()
            if not retailer:return error('Retailer not found.',404)
            config=json.loads(retailer['payload']);existing=config.get('stores',[])
            known={store['key'].casefold() for store in existing}
            additions=[{**store,'status':'Active','exception':False,'address':''} for store in metrics.get('newStores') or [] if store['key'].casefold() not in known]
            if additions:
                try:
                    updated=validate_retailer({**config,'stores':existing+additions})
                    updated['stores']=assign_store_codes(updated['stores'],existing,db)
                except ValueError as exc:return error('New stores require review before approval: '+str(exc))
                db.execute('UPDATE retailer_configs SET payload=? WHERE id=?',(json.dumps(updated),job['retailer_id']))
            metrics['newStoresAddedOnApproval']=len(additions)
            db.execute('UPDATE batch_jobs SET metrics=? WHERE id=?',(json.dumps(metrics),jid))
"""+needle)
p.write_text(s)
print('Audit metrics wired')
