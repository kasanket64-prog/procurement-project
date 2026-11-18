'use strict';
// Showcase examples are illustrative, separate from imported buyer data.
const examples = {
  recovery: {title:'Supplier replacement review', metrics:[['1','Feasible offer'],['1','Evidence unavailable'],['1','Disrupted supplier excluded']], offers:[['REVIEWABLE','quote-3 · feasible','INR 9,500 · Full requested quantity. Documented capacity: 10 each. Human review required.'],['EVIDENCE GAP','quote-2 · unavailable','INR 9,000 · Capacity evidence missing. A lower price does not establish feasibility.']]},
  evidence: {title:'Trace the evidence', metrics:[['3','Illustrative source events'],['1','Correction recorded'],['0','Purchase authorizations']], offers:[['SOURCE HISTORY','Original → correction','The original event stays visible. A subsequent correction changes the effective record.'],['REVIEW REQUIRED','Quality is not authenticity','Timestamp and schema checks do not prove that a supplier document is genuine.']]},
  scenarios: {title:'Explore a different constraint', metrics:[['10','Requested units'],['INR 9,000','Illustrative budget'],['0','Offers within budget']], offers:[['BASELINE','Documented offer · INR 9,500','A full-quantity offer exceeds this illustrative budget by INR 500.'],['HUMAN DECISION','Adjust assumptions, then review','Changing a demo constraint does not change the buyer request or authorize a purchase.']]}
};
const tabs = [...document.querySelectorAll('[role="tab"]')];
function selectExample(tab) {
  const example = examples[tab.dataset.view];
  tabs.forEach(item => {item.setAttribute('aria-selected', String(item === tab)); item.tabIndex = item === tab ? 0 : -1;});
  document.getElementById('example').setAttribute('aria-labelledby', tab.id);
  document.getElementById('example-title').textContent = example.title;
  example.metrics.forEach(([value,label],i) => {document.getElementById(`metric-${i}`).textContent=value;document.getElementById(`label-${i}`).textContent=label;});
  example.offers.forEach(([status,title,detail],i) => {document.getElementById(`status-${i}`).textContent=status;document.getElementById(`offer-${i}`).textContent=title;document.getElementById(`detail-${i}`).textContent=detail;});
}
tabs.forEach((tab,index) => {
  tab.addEventListener('click', () => selectExample(tab));
  tab.addEventListener('keydown', event => {
    const target = {ArrowRight:(index+1)%tabs.length,ArrowLeft:(index+tabs.length-1)%tabs.length,Home:0,End:tabs.length-1}[event.key];
    if (target === undefined) return;
    event.preventDefault(); selectExample(tabs[target]); tabs[target].focus();
  });
});
const scene = document.querySelector('.scene');
if (window.matchMedia('(hover:hover) and (pointer:fine) and (prefers-reduced-motion:no-preference)').matches) {
  scene.addEventListener('pointermove', event => {
    const box=scene.getBoundingClientRect();
    scene.style.setProperty('--orb-x', `${((event.clientX-box.left)/box.width-.5)*16}px`);
    scene.style.setProperty('--orb-y', `${((event.clientY-box.top)/box.height-.5)*12}px`);
  });
  scene.addEventListener('pointerleave', () => {scene.style.setProperty('--orb-x','0px');scene.style.setProperty('--orb-y','0px');});
}
