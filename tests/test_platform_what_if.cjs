// Run with: node --test tests/test_platform_what_if.cjs
const {readFileSync} = require('node:fs');
const {join} = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const {test} = require('node:test');
const source = readFileSync(join(__dirname, '../ml/procurement_platform_template.html'), 'utf8');
const context = vm.createContext({});
vm.runInContext(source.slice(source.indexOf('function rankDemo('), source.indexOf('function showComparison(')), context);
vm.runInContext(source.slice(source.indexOf('function parseReadiness('), source.indexOf('function renderReadiness(')), context);
const readiness = {
  schema_version:'1.0',status:'checks_complete',checked_at:'2026-11-14T12:00:00+00:00',
  model_ready:false,purchase_authorized:false,human_review_required:true,
  stages:[
    {key:'snapshots',status:'passed',summary:{snapshot_rows:1,active_order_lines:1,correction_rows:0}},
    {key:'receipts',status:'passed',summary:{active_order_lines:1,receipt_events:1}},
    {key:'labels',status:'passed',summary:{label_counts:{unknown:1}}},
  ],
};
test('readiness preview accepts versioned aggregate reports and UTF-8 BOM', () => {
  assert.equal(context.parseReadiness('\uFEFF'+JSON.stringify(readiness)).stages[2].summary.label_counts.unknown,1);
  const blocked=structuredClone(readiness);
  blocked.status='blocked';
  blocked.stages[1]={key:'receipts',status:'blocked',reason:'Missing file'};
  blocked.stages[2]={key:'labels',status:'skipped',reason:'Resolve receipts'};
  assert.equal(context.parseReadiness(JSON.stringify(blocked)).status,'blocked');
});
test('readiness preview rejects unsafe authority flags, invalid order and summaries', () => {
  for(const change of [
    r=>{r.model_ready=true;},r=>{r.purchase_authorized=true;},r=>{r.human_review_required=false;},
    r=>{delete r.schema_version;},r=>{r.checked_at='invalid';},r=>{r.stages.reverse();},
    r=>{r.checked_at='2026-02-30T12:00:00Z';},
    r=>{r.stages[0].status='skipped';},r=>{r.stages[0].summary.snapshot_rows=-1;},
    r=>{r.stages[2].summary.label_counts=1;},r=>{r.stages[2].summary.label_counts={unknown:'1'};},
    r=>{r.stages[2].summary.label_counts={invented:1};},r=>{r.status='blocked';},
  ]){
    const invalid=structuredClone(readiness);change(invalid);
    assert.throws(()=>context.parseReadiness(JSON.stringify(invalid)));
  }
  assert.throws(()=>context.parseReadiness('{bad'));
  assert.throws(()=>context.parseReadiness(' '.repeat(1048577)));
});
function previewDom(){
  const elements=Object.fromEntries(['readiness-file','readiness-cards','readiness-status','readiness-error','clear-readiness'].map(id=>[id,{
    value:'',textContent:'',children:[],replaceChildren(){this.children=[];},
  }]));
  const ui=vm.createContext({
    el:id=>elements[id],n:(tag,text)=>({tag,text}),
    card:(id,badge,title)=>{const node={badge,title,children:[],append(...items){this.children.push(...items);}};elements[id].children.push(node);return node;},
  });
  vm.runInContext(source.slice(source.indexOf('function parseReadiness('),source.indexOf('let currentDemo=')),ui);
  return elements;
}
test('preview handler renders a valid report, rejects invalid replacement and clears', async () => {
  const dom=previewDom();
  const open=report=>dom['readiness-file'].onchange({target:{files:[{size:100,text:async()=>JSON.stringify(report)}]}});
  await open(readiness);
  assert.equal(dom['readiness-cards'].children.length,3);
  const invalid=structuredClone(readiness);invalid.purchase_authorized=true;
  await open(invalid);
  assert.equal(dom['readiness-cards'].children.length,0);
  assert.match(dom['readiness-error'].textContent,/Cannot preview/);
  dom['clear-readiness'].onclick();
  assert.equal(dom['readiness-error'].textContent,'');
  assert.equal(dom['readiness-status'].textContent,'No report selected.');
  assert.equal(dom['readiness-file'].value,'');
});
test('clear and newer file selection prevent stale asynchronous imports', async () => {
  const dom=previewDom();
  let resolve;
  const pending=dom['readiness-file'].onchange({target:{files:[{size:100,text:()=>new Promise(done=>{resolve=done;})}]}});
  dom['clear-readiness'].onclick();
  resolve(JSON.stringify(readiness));await pending;
  assert.equal(dom['readiness-cards'].children.length,0);
  assert.equal(dom['readiness-status'].textContent,'No report selected.');
  const slow=dom['readiness-file'].onchange({target:{files:[{size:100,text:()=>new Promise(done=>{resolve=done;})}]}});
  await dom['readiness-file'].onchange({target:{files:[{size:1048577,text:()=>{throw Error('Must not read oversized file');}}]}});
  resolve(JSON.stringify(readiness));await slow;
  assert.equal(dom['readiness-cards'].children.length,0);
  assert.equal(dom['readiness-status'].textContent,'No report loaded.');
});
test('generated offline app contains the same valid script as its template', () => {
  const script = html => html.slice(html.indexOf("'use strict';"), html.lastIndexOf('</script>'));
  const generated = readFileSync(join(__dirname, '../ml/procurement_platform.html'), 'utf8');
  new vm.Script(script(source));
  assert.equal(script(generated), script(source));
});
const inputs = {product:'Widget', country:'', priority:'balanced', quantity:10, budget:null, totalBudget:1000};
const rows = [
  {supplier_id:'A',supplier_name:'Same',item:'Widget',supplier_country:'India',avg_unit_price:80,historical_orders:20,on_time_rate:95,rejection_rate:2},
  {supplier_id:'B',supplier_name:'Same',item:'Widget',supplier_country:'India',avg_unit_price:120,historical_orders:100,on_time_rate:85,rejection_rate:3},
];
test('total budget follows quantity and keeps the pre-filter experience reference', () => {
  const before = JSON.stringify({rows,inputs});
  const baseline = context.rankDemo(rows, inputs);
  assert.equal(baseline.length,1);
  assert.equal(baseline[0].parts[2],5);
  assert.equal(context.rankDemo(rows,{...inputs,quantity:20}).length,0);
  assert.equal(context.rankDemo(rows,{...inputs,totalBudget:1500}).length,2);
  assert.equal(context.rankDemo(rows,{...inputs,totalBudget:1500,budget:100}).length,1);
  assert.equal(JSON.stringify({rows,inputs}),before);
});
test('priority, country and supplier ID tie-breaking remain deterministic', () => {
  const all = {...inputs,totalBudget:null};
  assert.equal(context.rankDemo(rows,{...all,country:'Germany'}).length,0);
  const price = context.rankDemo(rows,{...all,priority:'price'});
  assert.equal(price.find(r=>r.supplier_id==='A').parts[3],50);
  const tied = [rows[0],{...rows[0],supplier_id:'C'}].reverse();
  assert.equal(context.rankDemo(tied,all).map(r=>r.supplier_id).join(','),'A,C');
});
