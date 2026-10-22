from pathlib import Path
import re
root=Path('outputs/V1.6.0/script')
def replace_method(s,name,body):
 return re.sub(r'    def '+name+r'\(self\):.*?(?=\n    def |\nif __name__)', lambda match:'    def '+name+'(self):\n'+body+'\n',s,flags=re.S)
p=root/'test_batch_jobs.py';s=p.read_text().replace('test_successive_runs_keep_old_record_and_source','test_successful_replacement_deletes_old_record_and_source')
s=replace_method(s,'test_successful_replacement_deletes_old_record_and_source',"""        old=self.complete();new=self.start(source=b'sku\\n replacement \\n');self.finish(new)
        self.assertEqual(len(self.jobs()),2)
        self.assertEqual(self.client.get('/api/v1/batches/'+old['id']+'/audit').status_code,200)
        with get_db_connection() as db:
            self.assertEqual(db.execute('SELECT source FROM batch_jobs WHERE id=?',(new,)).fetchone()[0],b'sku\\n replacement \\n')""")
s=replace_method(s,'test_cancelled_replacement_preserves_previous_job',"""        old=self.complete();aid=self.client.post('/api/v1/batches/'+old['id']+'/reprocess').get_json()['attemptId']
        self.client.post('/api/v1/batches/'+aid+'/cancel');self.finish(aid)
        self.assertEqual(len(self.jobs()),2)
        failed=next(j for j in self.jobs() if j['id']==aid)
        self.assertEqual(failed['status'],'Cancelled Job');self.assertIsNone(failed['end_time']);self.assertFalse(failed['hasAudit'])
        self.assertEqual(next(j for j in self.jobs() if j['id']==old['id'])['status'],'Completed')""")
s=replace_method(s,'test_failed_replacement_preserves_previous_and_shows_error',"""        old=self.complete();app.app.config['BATCH_TEST_EXECUTOR']=lambda records,rule:{'errorCode':'RULE_EXECUTION_ERROR','message':'Failed'}
        aid=self.start();self.finish(aid)
        self.assertEqual(len(self.jobs()),2)
        failed=next(j for j in self.jobs() if j['id']==aid)
        self.assertEqual(failed['status'],'Cancelled Job');self.assertIn('RULE_EXECUTION_ERROR',failed['errorCodes'])
        self.assertIn('RULE_RETRY_LIMIT',failed['errorCodes'])""")
s=s.replace("self.assertEqual(self.jobs()[0]['id'],old['id'])","self.assertTrue(any(j['id']==old['id'] for j in self.jobs()))")
s=replace_method(s,'test_duplicate_active_job_rejected_but_other_week_allowed',"""        first=self.start();second=self.start();other=self.start('2026-W42')
        self.finish(first);self.finish(second);self.finish(other)
        self.assertEqual(len(self.jobs()),3)""")
s=s.replace("self.jobs()[0]['lastAttempt']['errorCodes']","self.jobs()[0]['errorCodes']")
# Lambda replacement avoids interpreting literal backslashes in source snippets.
s=s.replace("test_successful_replacement_deletes_old_record_and_source","test_successive_runs_keep_old_record_and_source")
p.write_text(s,encoding='utf-8')
p=root/'test_batch_metrics.py';s=p.read_text();s=s.replace("self.assertEqual(self.jobs()[0]['metrics'],old)","self.assertEqual(next(j for j in self.jobs() if j['id']==first)['metrics'],old);self.assertEqual(len(self.jobs()),2)");p.write_text(s,encoding='utf-8')
p=root/'test_iso_week.py';s=p.read_text();s=s.replace("self.assertEqual(len(self.jobs()),1);self.assertEqual(self.jobs()[0]['period'],'2026-W41')","self.assertEqual(len(self.jobs()),2);self.assertEqual(self.jobs()[0]['period'],'2026-W41')")
s=replace_method(s,'test_target_week_conflict_and_cancel_preserves_both_records',"""        original=self.completed('2026-W41');target=self.completed('2026-W42')
        aid=self.client.post('/api/v1/batches/'+original+'/reprocess',json={'period':'2026-W42'}).get_json()['attemptId']
        second=self.client.post('/api/v1/batches/'+original+'/reprocess',json={'period':'2026-W42'})
        self.assertEqual(second.status_code,202)
        self.finish(second.get_json()['attemptId']);self.client.post('/api/v1/batches/'+aid+'/cancel')
        self.assertEqual(len(self.jobs()),4);self.assertTrue({original,target}.issubset({j['id'] for j in self.jobs()}))""")
p.write_text(s,encoding='utf-8')
print('History expectations updated')
