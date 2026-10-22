from pathlib import Path
p=Path('outputs/V1.9.0/frontend-github/src/BatchLogs.jsx');s=p.read_text(encoding='utf-8')
s=s.replace('useEffect,useState','useEffect,useState,useRef')
s=s.replace(' useEffect(()=>setPreprocessing(null),[file,retailerId,period,storeIdField,reprocessJob,reprocessPeriod]);',' const checkRequest=useRef(0);\n useEffect(()=>{checkRequest.current++;setPreprocessing(null);},[file,retailerId,period,storeIdField,reprocessJob,reprocessPeriod]);')
s=s.replace("if(!preprocessing?.ready){const checked=", "if(!preprocessing?.ready){const serial=checkRequest.current;const checked=")
s=s.replace('setPreprocessing(checked.report);return;', 'if(serial===checkRequest.current)setPreprocessing(checked.report);return;')
p.write_text(s,encoding='utf-8')
print('Stale preprocessing response guard added')
