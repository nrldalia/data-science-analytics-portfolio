import fs from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
const runtime='C:/Users/nurul/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const require=createRequire(runtime+'/artifact-loader.cjs');
const {Workbook}=await import(pathToFileURL(require.resolve('@oai/artifact-tool')).href);
const out=path.resolve('outputs/V1.5.0_Sample_Data');
await fs.mkdir(out,{recursive:true});
const header=['Transaction ID','Store ID','Store Name','SKU','Product Name','Category','Sale Date','Quantity','Unit Price','Sales'];
const stores={S001:'MY6 Mart Central',S002:'MY6 Mart North',S003:'MY6 Mart South',S004:'MY6 Mart East'};
function rows(count,ids,week){return Array.from({length:count},(_,i)=>{
 const id=ids[i%ids.length], qty=1+i%5, price=3.5+(i%7)*2;
 return [`TX${week}-${String(i+1).padStart(4,'0')}`,id,`  ${stores[id]}  `,` sku-${String(100+i%8).padStart(3,'0')} `,i%2?'St. Bread':'Fresh Milk',i%2?' BAKERY ':' DAIRY ',`${String(week===40?28+i%3:week===41?5+i%4:12+i%4).padStart(2,'0')}/${week===40?'09':'10'}/2026`,String(qty),price.toFixed(2),(qty*price).toFixed(2)];
});}
const baseline=rows(20,['S001','S002','S003'],40);
const main=rows(30,['S001','S002','S004'],41);
const smaller=rows(10,['S001','S002','S004'],42);
const bad=rows(6,['S001','S002','S004'],41);
bad[0][0]=bad[1][0];bad[1][1]='';bad[2][3]='BAD-SKU';bad[3][6]='31/02/2026';bad[4][9]='not-a-number';bad[5][9]='-25.00';
const datasets=[
 ['V1.5.0_Store_Table_Reference.csv',[['Retailer Store ID','Retailer Store Name','Status','Exception','Store Address'],...['S001','S002','S003'].map((id,i)=>[id,stores[id],'Active','No',`${i+1} Test Road, Kuala Lumpur`])]],
 ['V1.5.0_Rules_Sample.csv',[header,...main.slice(0,8)]],
 ['V1.5.0_Batch_2026-W40.csv',[header,...baseline]],
 ['V1.5.0_Batch_2026-W41.csv',[header,...main]],
 ['V1.5.0_Batch_2026-W42.csv',[header,...smaller]],
 ['V1.5.0_Failure_Test_2026-W41.csv',[header,...bad]]
];
const quote=v=>/[",\r\n]/.test(String(v))?'"'+String(v).replaceAll('"','""')+'"':String(v);
const summary=[];
for(const [name,matrix] of datasets){
 const wb=Workbook.create(), sheet=wb.worksheets.add('Sample');
 sheet.getRangeByIndexes(0,0,matrix.length,matrix[0].length).values=matrix;
 wb.recalculate();
 const authored=sheet.getRangeByIndexes(0,0,matrix.length,matrix[0].length).values;
 // CSV carries raw test strings, including intentional spaces and malformed dates.
 const csv=authored.map(row=>row.map(v=>quote(v??'')).join(',')).join('\r\n')+'\r\n';
 await fs.writeFile(path.join(out,name),csv,'utf8');
 summary.push({name,rows:matrix.length-1,bytes:Buffer.byteLength(csv)});
}
await fs.writeFile(path.resolve('work/sample_data_manifest.json'),JSON.stringify(summary,null,2));
console.log(JSON.stringify(summary));
