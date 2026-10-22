const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const nodes=new Map();
class Element {
 constructor(id){this.id=id;this.hidden=true;this.checked=false;this.value='';this.disabled=false;this.style={};this.dataset={};this.events={};this.attributes={};this.span={textContent:''};this.markup='';this.inputs=[];}
 set innerHTML(value){this.markup=value;this.inputs=[...value.matchAll(/<input type="checkbox" value="([^"]*)" ([^>]*)>/g)].map(m=>{const input=new Element('input');input.value=m[1];input.checked=m[2].includes('checked');return input;});}
 get innerHTML(){return this.markup;}
 querySelector(value){return value==='span'?this.span:null;}
 querySelectorAll(value){return value==='input:checked'?this.inputs.filter(i=>i.checked):value==='input'?this.inputs:[];}
 addEventListener(name,fn){this.events[name]=fn;}
 setAttribute(name,value){this.attributes[name]=value;}
 focus(){}
}
const html=fs.readFileSync(__dirname+'/kpi-record-design.html','utf8');
for(const m of html.matchAll(/\bid="([^"]+)"/g))nodes.set(m[1],new Element(m[1]));
const root=nodes.get('kpi-design-preview');root.querySelector=value=>nodes.get(value.slice(1));
root.querySelectorAll=value=>value==='.kp-picker'?[...nodes.values()].filter(n=>n.id.endsWith('-menu')):value==='[aria-expanded]'?[...nodes.values()].filter(n=>n.id.endsWith('-button')):value==='[data-retailer]'?[...nodes.get('kp-rows').innerHTML.matchAll(/data-retailer="([^"]*)"/g)].map(m=>{const node=new Element('retailer');node.dataset.retailer=m[1];return node;}):[];
const code=html.match(/<script>([\s\S]*?)<\/script>/)[1];
vm.runInNewContext(code,{document:{getElementById:()=>root},window:{addEventListener(){},matchMedia:()=>({matches:false})},getComputedStyle:()=>({colorScheme:'light'})});
const count=()=>[...nodes.get('kp-rows').innerHTML.matchAll(/<tr>/g)].length;
const select=(id,value)=>{const menu=nodes.get(id),input=menu.inputs.find(i=>i.value===value);assert.ok(input);input.checked=true;input.events.change();};
assert.equal(count(),6);select('kp-retailer-menu','Retailer A');assert.equal(count(),6);assert.ok(nodes.get('kp-rows').innerHTML.includes('MY60000022'));
nodes.get('kp-store-enabled').onchange({target:{checked:true}});assert.equal(nodes.get('kp-store-kind').disabled,false);
select('kp-store-menu','MY60000024');assert.equal(count(),2);
nodes.get('kp-store-kind').onchange({target:{value:'retailer'}});assert.ok(nodes.get('kp-store-menu').innerHTML.includes('A-002'));
nodes.get('kp-display-choice').value='sales';nodes.get('kp-apply-dialog').onclick();assert.ok(nodes.get('kp-rows').innerHTML.includes('<span>Qty</span>'));
select('kp-year-menu','2025');assert.equal(count(),4);select('kp-period-menu','Monthly');assert.equal(count(),6);
nodes.get('kp-theme').onclick();assert.equal(root.style.colorScheme,'dark');nodes.get('kp-theme').onclick();assert.equal(root.style.colorScheme,'light');
console.log('Mockup runtime checks passed: overall totals, all-store drill-down, store filter/identifier, multiple years/periods, trend display and theme toggle.');
