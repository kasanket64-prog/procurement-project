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
    el:id=>elements[id],n:(tag,text)=>({tag,text,children:[],append(...items){this.children.push(...items);}}),
    card:(id,badge,title)=>{const node={badge,title,children:[],append(...items){this.children.push(...items);}};elements[id].children.push(node);return node;},
  });
  vm.runInContext(source.slice(source.indexOf('function parseReadiness('),source.indexOf('let currentDemo=')),ui);
  return elements;
}

function sourceReport(){
  return {...structuredClone(readiness),source_preview:['order_snapshots.csv','receipt_events.csv','outcome_reviews.csv','decision_signals.csv'].map(file=>({
    file,status:'passed',expected_columns:['source_ref','known_at'],missing_columns:[],unexpected_column_count:0,duplicate_column_count:0,exact_order:true,
  }))};
}
function timelineReport(){
 return {schema_version:'1.0',report_kind:'order_timeline',status:'timeline_available',order_line_id:'line',checked_at:readiness.checked_at,model_ready:false,purchase_authorized:false,human_review_required:true,events:[
  {kind:'receipt:accepted',record_id:'accept',event_at:'2026-11-05T00:00:00Z',known_at:'2026-11-06T00:00:00Z',captured_at:'2026-11-07T00:00:00Z',source_ref:'<script>private</script>',supersedes_id:'',reverses_event_id:'',superseded:false,details:{quantity:'4',unit:'each'}},
  {kind:'receipt:reversal',record_id:'undo',event_at:'2026-11-09T00:00:00Z',known_at:'2026-11-10T00:00:00Z',captured_at:'2026-11-11T00:00:00Z',source_ref:'source',supersedes_id:'',reverses_event_id:'accept',superseded:false,details:{quantity:'2',unit:'each'}},
 ]};
}
test('timeline parser validates authority, clocks, identities and history links',()=>{
 assert.equal(context.parseTimeline('\uFEFF'+JSON.stringify(timelineReport())).events.length,2);
 for(const change of [r=>{r.model_ready=true;},r=>{r.events.reverse();},r=>{r.events[1].reverses_event_id='missing';},r=>{r.events[0].superseded=true;},r=>{r.events[0].kind='invented';},r=>{r.events[0].known_at='2026-02-30T00:00:00Z';},r=>{r.events[0].captured_at='2027-01-01T00:00:00Z';},r=>{r.events[0].details.extra='private';},r=>{r.events[0].supersedes_id='accept';},r=>{r.events.push(r.events[1]);}]){
  const r=timelineReport();change(r);assert.throws(()=>context.parseTimeline(JSON.stringify(r)));
 }
 assert.throws(()=>context.parseTimeline(' '.repeat(1048577)));
});
test('timeline import renders text and links, rejects invalid replacement and clears',async()=>{
 const dom=previewDom(),r=timelineReport();
 const open=report=>dom['readiness-file'].onchange({target:{files:[{size:100,text:async()=>JSON.stringify(report)}]}});
 await open(r);assert.equal(dom['readiness-cards'].children.length,3);
 assert.match(dom['readiness-status'].textContent,/2 recorded events/);
 const accepted=dom['readiness-cards'].children[1].children[1];
 assert.equal(accepted.tag,'details');assert(accepted.children.some(p=>p.text==='source ref: <script>private</script>'));
 const reversed=dom['readiness-cards'].children[2].children[1];
 assert(reversed.children.some(p=>p.text==='reverses event id: accept'));
 r.events[1].reverses_event_id='missing';await open(r);
 assert.equal(dom['readiness-cards'].children.length,0);assert.match(dom['readiness-error'].textContent,/Cannot preview/);
 const blocked={schema_version:'1.0',report_kind:'order_timeline',status:'blocked',reason:'Setup blocked',events:[],model_ready:false,purchase_authorized:false,human_review_required:true};
 await open(blocked);assert.equal(dom['readiness-cards'].children.length,1);
 blocked.order_line_id='private';await open(blocked);assert.equal(dom['readiness-cards'].children.length,0);
 await open(timelineReport());dom['clear-readiness'].onclick();assert.equal(dom['readiness-cards'].children.length,0);
});
test('source preview validates supplied mappings and rejects malformed or inconsistent metadata',()=>{
  assert.equal(context.parseReadiness(JSON.stringify(sourceReport())).source_preview.length,4);
  for(const change of [
    r=>{r.source_preview={};},r=>{r.source_preview=[];},r=>{r.source_preview.reverse();},
    r=>{r.source_preview[0].expected_columns=['<script>'];},r=>{r.source_preview[0].expected_columns=['x','x'];},
    r=>{r.source_preview[0].missing_columns=['invented'];},r=>{r.source_preview[0].unexpected_column_count=-1;},
    r=>{r.source_preview[0].duplicate_column_count='0';},r=>{r.source_preview[0].exact_order=false;},
    r=>{r.source_preview[0].missing_columns=['source_ref'];},r=>{delete r.source_preview[0].exact_order;},
  ]){const report=sourceReport();change(report);assert.throws(()=>context.parseReadiness(JSON.stringify(report)));}
});
test('source preview renders blocked columns safely, clears and preserves legacy reports',async()=>{
  const dom=previewDom(),report=sourceReport();
  report.status='blocked';report.stages[2]={key:'labels',status:'blocked',reason:'Schema error'};
  Object.assign(report.source_preview[3],{status:'blocked',reason:'<script>untrusted</script>',missing_columns:['known_at'],exact_order:false});
  const open=r=>dom['readiness-file'].onchange({target:{files:[{size:100,text:async()=>JSON.stringify(r)}]}});
  await open(report);
  assert.equal(dom['readiness-cards'].children.length,8);
  const last=dom['readiness-cards'].children[7];
  assert.equal(last.children[0].text,'<script>untrusted</script>');
  assert.match(last.children[1].text,/Missing: known_at/);
  assert.equal(last.children[2].tag,'details');
  dom['clear-readiness'].onclick();assert.equal(dom['readiness-cards'].children.length,0);
  await open(readiness);assert.equal(dom['readiness-cards'].children.length,3);
  report.source_preview=[];await open(report);
  assert.equal(dom['readiness-cards'].children.length,4);
  assert.match(dom['readiness-cards'].children[3].children[1].text,/skipped/);
});
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
