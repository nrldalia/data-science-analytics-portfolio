from pathlib import Path
root=Path(__file__).resolve().parent.parent/'outputs/V1.14.0'
p=root/'frontend-github/src/WorkflowRules.jsx';s=p.read_text(encoding='utf-8').replace("prior.datasets[draft.rightInputId]||[]))}","prior.datasets[draft.rightInputId]||[])}").replace('Preview validates the selected fields; weekly KPI checks run during batch processing.','Weekly KPI checks run during batch processing on the final mapped output.');p.write_text(s,encoding='utf-8')
p=root/'script/test_file_workflow.py';s=p.read_text(encoding='utf-8').replace("{'inputFiles':[{'id':'a'},{'id':'b'}],'pipeline':pipeline}","{'inputFiles':[{'id':'a'},{'id':'b'}],'primaryInputId':'a','pipeline':pipeline}");p.write_text(s,encoding='utf-8')
print('Preserved column order and fixed dropdown syntax.')
