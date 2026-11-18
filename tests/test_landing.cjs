const {test}=require('node:test');
const assert=require('node:assert/strict');
const {readFileSync,existsSync}=require('node:fs');
const {join}=require('node:path');
const vm=require('node:vm');
const root=join(__dirname,'../ml');
function setup(motion=false){
  const elements=new Map();
  const element=id=>({id,dataset:{view:id.slice(4)},attributes:{},listeners:{},style:{setProperty(){}},setAttribute(k,v){this.attributes[k]=v;},addEventListener(k,v){this.listeners[k]=v;},focus(){this.focused=true;}});
  const tabs=['evidence','scenarios','recovery'].map(v=>element('tab-'+v));
  const scene=element('scene');
  const document={querySelectorAll:()=>tabs,querySelector:()=>scene,getElementById:id=>{if(!elements.has(id))elements.set(id,element(id));return elements.get(id);}};
  vm.runInNewContext(readFileSync(join(root,'landing.js'),'utf8'),{document,window:{matchMedia:()=>({matches:motion})}});
  return {tabs,scene,elements};
}
test('tabs change example, selection, labels and keyboard focus',()=>{
  const {tabs,elements}=setup();
  tabs[0].listeners.click();
  assert.equal(elements.get('example-title').textContent,'Trace the evidence');
  assert.equal(elements.get('example').attributes['aria-labelledby'],'tab-evidence');
  assert.equal(tabs[0].attributes['aria-selected'],'true');
  assert.equal(tabs[2].tabIndex,-1);
  let prevented=false;
  tabs[0].listeners.keydown({key:'ArrowLeft',preventDefault(){prevented=true;}});
  assert.ok(prevented);assert.ok(tabs[2].focused);
  assert.equal(elements.get('offer-0').textContent,'quote-3 · feasible');
  tabs[2].listeners.keydown({key:'Home',preventDefault(){}});
  assert.ok(tabs[0].focused);
  tabs[0].listeners.keydown({key:'ArrowRight',preventDefault(){}});
  assert.equal(elements.get('metric-1').textContent,'INR 9,000');
  tabs[1].listeners.keydown({key:'End',preventDefault(){}});
  assert.equal(tabs[2].attributes['aria-selected'],'true');
});
test('reduced motion does not attach pointer animation',()=>{
  assert.deepEqual(Object.keys(setup().scene.listeners),[]);
  assert.deepEqual(Object.keys(setup(true).scene.listeners),['pointermove','pointerleave']);
});
test('primary action and selected tab text meet 4.5:1 contrast',()=>{
  const css=readFileSync(join(root,'landing.css'),'utf8');
  const luminance=hex=>{
    const rgb=hex.match(/../g).map(value=>parseInt(value,16)/255)
      .map(value=>value<=0.04045?value/12.92:((value+0.055)/1.055)**2.4);
    return rgb[0]*0.2126+rgb[1]*0.7152+rgb[2]*0.0722;
  };
  const tokens=Object.fromEntries([...css.matchAll(/--([\w-]+):#([0-9a-f]{6})/g)].map(m=>[m[1],m[2]]));
  for(const selector of ['.button.primary','.button.primary:hover','.tabs button[aria-selected=true]']){
    const escaped=selector.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
    const block=css.match(new RegExp(escaped+'\\{([^}]+)\\}'))[1];
    const background=block.match(/background:var\(--([\w-]+)\)/)[1];
    assert.ok((1.05/(luminance(tokens[background])+0.05))>=4.5,selector);
  }
});
test('local links and assets exist, fragments resolve and font is WOFF2',()=>{
  const html=readFileSync(join(root,'landing.html'),'utf8');
  const ids=new Set([...html.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]));
  for(const [,target] of html.matchAll(/(?:href|src)="([^"]+)"/g)){
    if(target.startsWith('#'))assert.ok(ids.has(target.slice(1)),target);
    else assert.ok(existsSync(join(root,target)),target);
  }
  assert.equal(readFileSync(join(root,'assets/InterVariable.woff2')).subarray(0,4).toString(),'wOF2');
  assert.ok(readFileSync(join(root,'assets/Inter-LICENSE.txt'),'utf8').includes('SIL OPEN FONT LICENSE'));
  assert.equal(readFileSync(join(root,'assets/glass-sphere.png')).subarray(1,4).toString(),'PNG');
});
