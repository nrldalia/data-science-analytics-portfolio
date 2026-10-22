from pathlib import Path
root=Path('outputs/V1.4.0')
p=root/'frontend-github/src/BatchLogs.jsx';s=p.read_text(encoding='utf-8').replace('<td className="p-2 font-mono text-rose-300">{entry.errorCode||\'\'}</td>', '<td className={`p-2 font-mono ${entry.result===\'Successful\'?\'text-emerald-300\':\'text-rose-300\'}`}>{[entry.executionCode,entry.errorCode].filter(Boolean).join(\' · \')}</td>');p.write_text(s,encoding='utf-8')
p=root/'script/test_batch_jobs.py';s=p.read_text(encoding='utf-8').replace("self.assertEqual([e['result'] for e in audit['entries']],['Successful','Successful'])", "self.assertEqual([e['result'] for e in audit['entries']],['Successful','Successful'])\n        self.assertEqual(audit['entries'][1]['executionCode'],'909')").replace("self.assertEqual([e['result'] for e in entries[1:]],['Fail Execution','Successful'])", "self.assertEqual([e['result'] for e in entries[1:]],['Fail Execution','Successful'])\n        self.assertEqual([e['executionCode'] for e in entries[1:]],['908','909'])");p.write_text(s,encoding='utf-8')
(root/'CHANGELOG_V1.4.0.md').write_text('''# V1.4.0 — Component rule popups

Enhances V1.3.0 with its V1.3.A1 and V1.3.A2 amendments. Replaces the component selector with Cleaning, Transformation and Validation buttons under a small Mandatory components label. Each opens a component Rules popup with rule selection, an editable description, prefilled Error 909: Successful at Execution and Error 908: Failure at Execution, plus Save and Cancel.

As clarified by the user, the table retains one row per individual rule. Popup Save appends one row; Cancel discards the draft. Existing reusable rules and Add New Rules remain supported. Table columns stay Components, Description, Sequence, Condition and Edit. Descriptions display as text. Edit opens only the description and execution messages. Condition opens a separate summary with its own Edit Condition button for field/operation settings and row conditions. Save Condition applies the draft; Cancel discards it. Save Configuration persists the ordered rules, descriptions and conditions. Rule/component/final previews remain available.

Batch rule audits add executionCode 909 for success and 908 for failure, while preserving specific diagnostic error codes and existing retry/cancellation behavior. The codes are prefilled rather than user-editable. Ingestion/approval audit entries retain their existing behavior. Old audits without these codes remain readable.

Keeps compact Data Streams action icons from V1.3.A2. Updates the existing single V1.3.A1.bat entry point to launch V1.4.0 on localhost port 5001. Preserves local data using SQLite backup; no data, samples or runtimes are included in GitHub snapshots.
''',encoding='utf-8')
(root/'README.md').write_text('''# DataFlow V1.4.0

Close the previous server window, then use the existing single V1.3.A1.bat launcher. It now opens V1.4.0 at http://127.0.0.1:5001/. Keep its window open. For a fresh checkout run Setup_Windows.bat, then Start_V1.4.0.bat.

In Retailer Data Setup → Rules Configure, click Cleaning, Transformation or Validation. Choose an individual rule, describe why it is used and click Save. Each saved draft adds one row. Cancel adds nothing. Execution messages are prefilled: Error 909 for Successful at Execution; Error 908 for Failure at Execution.

Use the row's Edit button to change its description. Use Condition → Edit Condition to change the field, operation parameters and matching-row condition. Save Condition applies these settings; Cancel leaves the row unchanged. Move rows with sequence arrows, inspect previews using a sample below 1 MB, and click Save Configuration to persist the full configuration.

The 909/908 execution codes appear in new rule audit entries alongside existing specific diagnostic codes. Existing retry, cancellation and replacement behavior is retained. Data Streams action icons remain compact.
''',encoding='utf-8')
print('Audit codes, validation assertions and documentation ready')
