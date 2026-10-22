from pathlib import Path
root=Path('outputs/V1.12.0')
p=root/'frontend-github/src/ConfigurationHistory.jsx';s=p.read_text(encoding='utf-8')
s=s.replace('<h4 className="font-semibold">Ordered Rules', '''{c.inputFiles?.length>0&&<><h4 className="font-semibold">Saved Input Files</h4><p className="text-xs text-slate-400">Sheet passwords are excluded from configuration snapshots.</p><div className="overflow-auto"><table className="w-full text-left text-xs"><thead><tr>{['Purpose','Filename','Type','Delimiter / Encoding','ZIP','Header / Max Columns','Read Mode','File Path'].map(h=><th className="p-2" key={h}>{h}</th>)}</tr></thead><tbody>{c.inputFiles.map(p=><tr className="border-t border-slate-600" key={p.id}><td className="p-2">{p.purpose}</td><td className="p-2">{p.filename}</td><td className="p-2">{p.fileType}</td><td className="p-2">{p.delimiter} / {p.encoding}</td><td className="p-2">{p.isZipFolder?'Yes':'No'}</td><td className="p-2">{p.headerRow} / {p.maxColumns}</td><td className="p-2">{p.readMode}</td><td className="p-2 break-all">{p.filePath}</td></tr>)}</tbody></table></div></>}<h4 className="font-semibold">Ordered Rules''',1)
p.write_text(s,encoding='utf-8')
p=root/'.gitignore';p.write_text(p.read_text()+'app-config.json\nsample_data/\n*.log\n',encoding='utf-8')
print('Input-file history display added')
