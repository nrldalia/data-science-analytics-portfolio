import assert from 'node:assert/strict';
import fs from 'node:fs';
const source=new URL('../outputs/V1.14.A1/frontend-github/src/',import.meta.url);
let saved=null,systemLight=false;
globalThis.window={localStorage:{getItem:()=>saved,setItem:(k,v)=>{saved=v;}},matchMedia:()=>({matches:systemLight})};
globalThis.document={documentElement:{dataset:{},style:{}}};
const {preferredTheme,applyTheme}=await import(new URL('theme.js',source));
assert.equal(preferredTheme(),'dark');systemLight=true;assert.equal(preferredTheme(),'light');
saved='dark';assert.equal(preferredTheme(),'dark');
applyTheme('light',true);assert.equal(document.documentElement.dataset.theme,'light');assert.equal(saved,'light');assert.equal(preferredTheme(),'light');assert.equal(document.documentElement.style.colorScheme,'light');
window.localStorage={getItem:()=>{throw Error('Storage disabled');},setItem:()=>{throw Error('Storage disabled');}};
assert.equal(preferredTheme(),'light');assert.equal(applyTheme('dark',true),'dark');assert.equal(document.documentElement.dataset.theme,'dark');
const css=fs.readFileSync(new URL('index.css',source),'utf8');
const dark=css.slice(css.indexOf(':root {'),css.indexOf(':root[data-theme="light"]'));
const light=css.slice(css.indexOf(':root[data-theme="light"]'),css.indexOf('body {'));
const vars=block=>Object.fromEntries([...block.matchAll(/--([\w-]+):\s*(#[0-9a-f]{6});/g)].map(m=>[m[1],m[2]]));
function luminance(hex){return hex.slice(1).match(/../g).map(v=>parseInt(v,16)/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4).reduce((sum,v,i)=>sum+v*[.2126,.7152,.0722][i],0);}
function contrast(a,b){const x=luminance(a),y=luminance(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05);}
let checks=0;
for(const [name,palette] of [['dark',vars(dark)],['light',{...vars(dark),...vars(light)}]]){
 for(const fg of ['color-slate-100','color-slate-400','color-slate-500','color-cyan-400','color-amber-300','color-emerald-300','color-rose-300']){
  const ratio=contrast(palette[fg],palette['panel-background']);assert.ok(ratio>=4.5,`${name} ${fg}: ${ratio.toFixed(2)}`);checks++;
 }
 assert.ok(contrast('#ffffff',palette['accent-solid'])>=4.5);checks++;
}
console.log(`Theme preference/storage checks passed; ${checks} text contrast checks passed (minimum 4.5:1).`);
