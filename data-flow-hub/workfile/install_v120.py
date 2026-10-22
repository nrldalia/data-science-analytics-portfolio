from pathlib import Path
import json, shutil
root=Path('outputs/V1.2.0')
shutil.copy('work/retailer_setup.py',root/'script/retailer_setup.py')
shutil.copy('work/RetailerSetup.jsx',root/'frontend-github/src/RetailerSetup.jsx')
p=root/'frontend-github/src/app.jsx';s=p.read_text(encoding='utf-8')
s="import RetailerSetup from './RetailerSetup';\n"+s
s=s.replace("useState('Clients')","useState('Retailer Data Setup')",1)
s=s.replace("{ name: 'Clients', icon: Building2 },","{ name: 'Retailer Data Setup', icon: Building2 },\n              { name: 'Clients', icon: Building2 },",1)
s=s.replace("{/* TAB 1: CLIENTS MODULE */}","{activeTab === 'Retailer Data Setup' && <RetailerSetup />}\n          {/* TAB 1: CLIENTS MODULE */}")
s=s.replace('V1.1.0','V1.2.0');p.write_text(s,encoding='utf-8')
p=root/'script/app.py';s=p.read_text(encoding='utf-8').replace("version='1.1.0'","version='1.2.0'").replace('V1.1.0','V1.2.0')
s=s.replace("if __name__=='__main__': app.run(host='127.0.0.1',port=5000,debug=False)","from retailer_setup import register_retailer_routes\nregister_retailer_routes(app, parse_upload, error)\n\nif __name__=='__main__':\n import sys\n if '--open-browser' in sys.argv:\n  import threading, time, urllib.request, webbrowser\n  def open_when_ready():\n   for _ in range(60):\n    try:\n     urllib.request.urlopen('http://127.0.0.1:5000/api/v1/health',timeout=1).close()\n     webbrowser.open('http://127.0.0.1:5000');return\n    except Exception: time.sleep(1)\n  threading.Thread(target=open_when_ready,daemon=True).start()\n app.run(host='127.0.0.1',port=5000,debug=False)")
p.write_text(s,encoding='utf-8')
p=root/'frontend-github/package.json';data=json.loads(p.read_text());data['version']='1.2.0';p.write_text(json.dumps(data,indent=2))
shutil.copytree('outputs/DataFlow_V1.1.0/frontend-github/node_modules',root/'frontend-github/node_modules',dirs_exist_ok=True)
print('V1.2.0 source and dependencies prepared.')
