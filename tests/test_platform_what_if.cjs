// Run with: node --test tests/test_platform_what_if.cjs
const {readFileSync} = require('node:fs');
const {join} = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const {test} = require('node:test');
const source = readFileSync(join(__dirname, '../ml/procurement_platform_template.html'), 'utf8');
const context = vm.createContext({});
vm.runInContext(source.slice(source.indexOf('function rankDemo('), source.indexOf('function showComparison(')), context);
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
