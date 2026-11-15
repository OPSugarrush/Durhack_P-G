/* Contextual business views built from the existing report. */
const movementColour=d=>d>0?'#18804b':d<0?'#b63938':'var(--muted)';
const bounded=v=>Math.max(0,Math.min(100,Number(v)||0));
function decisionBrief(c,reportIsExample){
 const products=(c.drivers||[]).map(p=>p.name+' ('+p.trips+' recent trips)').join(', ')||'No resolved recent products';
 return [c.name+' — investigation brief', 'Periods: '+ranges().join(' versus '), 'Evidence: '+c.status,
  'Change: '+c.change+' trips per 100, across '+c.comparable+' comparable buyers.',
  'Products to examine: '+products, 'Next step: '+c.action,
  'Before deciding: check retailer availability, changes in receipt coverage, basket size and seasonal explanations.',
  'Experiment: define one intervention for the relevant category buyers, alongside an unchanged comparison group. Set the success threshold before starting.',
  'Measure: repeat category purchases, recorded spend and shopper feedback over a comparable follow-up period.',
  'Limits: '+(reportIsExample?'synthetic observations':'receipt observations')+'; no causal uplift, margin or investment return is estimated. Brand comparisons use a separate category-buyer cohort.'].join('\n\n');
}
function decisionPanel(c){return '<div class="decision-summary"><h3>Products to investigate</h3>'+((c.drivers||[]).map(p=>'<p>'+esc(p.name)+' · '+p.trips+' recent trips</p>').join('')||'<p>No resolved recent products.</p>')+'<button class="secondary" id="download-brief">Download investigation brief</button></div>';}
function historyLink(c,buyer,all=false){
 const i=report.outlook.indexOf(c), origin=encodeURIComponent(location.hash.slice(1)||'outlook');
 return '#brand-history/'+i+'/'+encodeURIComponent(buyer||'_')+'/'+(all?'all':'changes')+'/'+origin;
}
function changedHistory(h){return ['Possible switch','First observed trial','Repeated trial'].includes(h.status)}
function findingBrands(f,c){
 // Category comparisons explain category findings. A mixed basket/mission does not imply brand competition.
 if(['Mixed basket','Shopping mission'].includes(f.kind))return '';
 return brandLink(f.label);
}
function brandLink(name){
 const i=(report.outlook||[]).findIndex(c=>c.name===name);
 if(i<0||report.outlook[i].brand_coverage<70||report.outlook[i].movements.brand.filter(m=>m.earlier!==null&&m.buyers>=5).length<2)return '';
 return '<p class="related-link"><a class="text-link" href="#brands/'+i+'/'+encodeURIComponent(location.hash.slice(1))+'">Compare brands within '+esc(name.toLowerCase())+' →</a></p>';
}
function outlookNavigation(active){
 return '<nav class="outlook-tabs" aria-label="Business analysis"><a href="#outlook" '+(active==='categories'?'aria-current="page"':'')+'>Category opportunities</a><a href="#brands" '+(active==='brands'?'aria-current="page"':'')+'>Brands & companies</a></nav>';
}
function brandsPage(parts){
 const cats=report.outlook||[];
 const origin=decodeURIComponent(parts.slice(2).join('/')||'outlook');
 const back=/^(outlook|evidence\/\d+(\/\d+)?)$/.test(origin)?origin:'outlook';
 view.innerHTML=outlookNavigation('brands')+(parts[2]?'<a class="back" href="#'+esc(back)+'">← Back to '+(back==='outlook'?'category opportunities':'finding')+'</a>':'')+intro('Understand brand choice','Compare brands within a category, distinguish company ownership, then explore the shoppers behind a change.');
 if(!cats.length){view.innerHTML+='<p>More comparable purchase history is needed for brand analysis.</p>';return}
 view.innerHTML+='<div class="bar"><label>Category <select id="brand-category">'+cats.map((c,i)=>'<option value="'+i+'">'+esc(c.name)+'</option>').join('')+'</select></label></div><div id="brand-analysis"></div>';
 const select=document.querySelector('#brand-category');select.value=String(Math.max(0,Math.min(cats.length-1,Number(parts[1])||0)));
 function draw(){document.querySelector('#brand-analysis').innerHTML=brandDetail(cats[Number(select.value)].name)}
 select.onchange=()=>{history.replaceState(null,'','#brands/'+select.value+'/'+encodeURIComponent(back));draw()};draw();
}
function brandRows(c,level,all=false){
 const rows=c.movements[level].filter(m=>m.earlier!==null&&m.buyers>=5).sort((a,b)=>Math.abs(b.recent-b.earlier)-Math.abs(a.recent-a.earlier)||b.recent-a.recent);
 const selected=all?rows:rows.filter(m=>Math.abs(m.recent-m.earlier)>=2).slice(0,3);
 if (!selected.length) return '<p>No movement meets the review threshold for these buyers.</p>';
 const tableRows=selected.map(m=>{
  const change=m.recent-m.earlier;
  const direction=change>0?'Up':change<0?'Down':'Steady';
  const delta=change===0?'':Math.abs(change).toFixed(1);
  return '<tr><th scope="row">'+esc(m.name)+'</th><td>'+m.earlier.toFixed(1)+'</td><td>'+m.recent.toFixed(1)+'</td><td>'+direction+' '+delta+'</td></tr>';
 }).join('');
 return '<table class="movement-table"><caption>Purchases per 100 category trips</caption><thead><tr><th scope="col">'+(level==='owner'?'Company':'Brand')+'</th><th scope="col">Earlier</th><th scope="col">Recent</th><th scope="col">Change</th></tr></thead><tbody>'+tableRows+'</tbody></table>';
}
function brandDetail(category){
 const c=report.outlook?.find(c=>c.name===category);if(!c)return '';
 const changed=c.histories.filter(changedHistory),coverage=c.brand_coverage;
 return '<section class="brand-context"><h2>Brand context</h2><p>'+ (coverage<70?'Too many products have unknown brands to draw a useful category comparison.': 'Comparing '+ranges().join(' with ')+' for buyers of '+esc(c.name.toLowerCase())+'.')+'</p>'+(coverage>=70?brandRows(c,'brand')+'<details class="quiet-details"><summary>View all brands and companies</summary><h3>Brands</h3>'+brandRows(c,'brand',true)+'<h3>Companies</h3>'+(c.owner_coverage>=70?brandRows(c,'owner',true):'<p>Company ownership is too incomplete for a useful comparison.</p>')+'</details>':'')+(changed.length?'<p><a class="text-link" href="'+historyLink(c,null)+'">Explore '+changed.length+' shoppers with observed brand changes →</a></p>':'')+'<details class="quiet-details"><summary>How this comparison works</summary><p>Each row uses the same buyers with at least two category trips in each period and at least five comparable buyers. Each buyer has equal weight. More than one brand can appear on a trip, so these are not market shares that sum to 100%. Movements are descriptive, not significance-tested brand claims.</p><p>'+c.brand_coverage+'% of item rows have recognised brands; '+c.owner_coverage+'% have known owners. First observed trials and possible switches are hypotheses within these records.</p></details></section>';
}
function shopperBrands(buyer){
 const rows=(report.outlook||[]).flatMap(c=>c.histories.filter(h=>h.buyer===buyer).map(h=>({c,h})));
 return '<section class="brand-context"><h2>Brand behaviour</h2><p class="muted">The individual’s observed choices within each category.</p>'+ (rows.map(({c,h})=>'<p><strong>'+esc(c.name)+'</strong> · '+esc(h.status)+' <a class="text-link" href="'+historyLink(c,buyer,true)+'">View history →</a></p>').join('')||'<p>More comparable purchase history is needed.</p>')+'</section>';
}
function brandHistory(parts){
 const c=report.outlook?.[Number(parts[1])];if(!c){view.innerHTML='<p>This category is no longer available.</p>'+btn('outlook','Business outlook');return}
 const buyer=decodeURIComponent(parts[2]||'_'), mode=parts[3],origin=decodeURIComponent(parts.slice(4).join('/')||'outlook');
 const back=/^(outlook|goals|brands(\/.*)?|evidence\/\d+(\/\d+)?)$/.test(origin)?origin:'outlook';
 const eligible=c.histories.filter(h=>(buyer==='_'||h.buyer===buyer)&&(mode==='all'||changedHistory(h)));
 view.innerHTML='<a class="back" href="#'+esc(back)+'">← Back to '+(back==='goals'?'shopper profiles':back==='outlook'?'business outlook':back.startsWith('brands')?'brand comparison':'finding')+'</a>'+intro(esc(c.name)+' · shopper histories','Follow the dated purchases behind these observations. Missing receipts or retailer changes can explain apparent switches.')+'<div class="bar"><label>Behaviour <select id="history-filter"><option>All</option>'+[...new Set(eligible.map(h=>h.status))].map(s=>'<option>'+esc(s)+'</option>').join('')+'</select></label><label>Shopper <input id="history-search" placeholder="Search shopper ID"></label></div><div id="history-list"></div>';
 let page=0;function draw(){const status=document.querySelector('#history-filter').value,q=document.querySelector('#history-search').value.toLowerCase(),rows=eligible.filter(h=>(status==='All'||h.status===status)&&h.buyer.toLowerCase().includes(q)),pages=Math.max(1,Math.ceil(rows.length/12));page=Math.min(page,pages-1);
 document.querySelector('#history-list').innerHTML='<p>'+rows.length+' matching shoppers</p>'+rows.slice(page*12,page*12+12).map(h=>'<details class="panel"><summary>'+esc(h.buyer)+' · '+esc(h.status)+'</summary>'+(h.previous?'<p>'+esc(h.previous)+' → '+esc(h.current)+' · '+esc(h.owner_movement)+'</p>':'')+(h.retailer_changed?'<p>Retailer coverage changed too; availability may explain the movement.</p>':'')+h.timeline.map(t=>'<p>'+esc(t.date)+' · Receipt '+esc(t.receipt)+' · '+esc(t.brands.join(', ')||'Unknown brand')+'</p>').join('')+'</details>').join('')+'<div class="bar"><button id="history-prev" '+(page===0?'disabled':'')+'>Previous</button><span>Page '+(page+1)+' of '+pages+'</span><button id="history-next" '+(page===pages-1?'disabled':'')+'>Next</button></div>';
 document.querySelector('#history-prev').onclick=()=>{page--;draw()};document.querySelector('#history-next').onclick=()=>{page++;draw()};}
 document.querySelector('#history-filter').onchange=()=>{page=0;draw()};document.querySelector('#history-search').oninput=()=>{page=0;draw()};draw();
}
function historicalOutlook(reportIsExample){
 const cats=report.outlook||[],reach=report.category_reach||[],top=reach[0];
 view.innerHTML=outlookNavigation('categories')+intro('Business outlook')+'<p class="muted">'+(reportIsExample?'Synthetic receipt evidence':'Receipt evidence')+' · '+ranges().join(' compared with ')+'.</p><div class="outlook-grid"><section><h2>Leading categories</h2><p>'+(top?esc(top.name)+' reaches '+top.buyers+' of '+top.total+' recently observed customers ('+top.reach.toFixed(0)+'%).':'Import identified customer histories to compare category reach.')+'</p><div id="reach-chart"></div></section><section class="brand-context"><h2>What’s gaining or losing ground?</h2><p>Changes in trips out of 100 across the same comparable buyers. Increases extend right; decreases extend left.</p><div id="change-chart"></div></section></div><div id="category-outlook"></div>';
 document.querySelector('#reach-chart').innerHTML=reach.map(c=>'<button class="chart-row" data-name="'+esc(c.name)+'"><strong>'+esc(c.name)+'</strong><svg viewBox="0 0 300 22" role="img" aria-label="'+c.reach.toFixed(1)+' percent reach"><rect width="300" height="18" y="2" rx="3" fill="var(--soft)"/><rect width="'+(bounded(c.reach)*3)+'" height="18" y="2" rx="3" fill="var(--ink)"/></svg><span>'+c.reach.toFixed(0)+'% · '+c.buyers+' customers</span></button>').join('');
 const scale=Math.max(1,...cats.map(c=>Math.abs(c.change)));
 document.querySelector('#change-chart').innerHTML=[...cats].sort((a,b)=>b.change-a.change).map(c=>{const w=Math.abs(c.change)/scale*140;return '<button class="chart-row" data-name="'+esc(c.name)+'"><strong>'+esc(c.name)+'</strong><svg viewBox="0 0 300 26" role="img" aria-label="'+c.change+' trips per 100"><line x1="150" x2="150" y1="0" y2="26" stroke="var(--muted)"/><rect x="'+(c.change<0?150-w:150)+'" y="4" width="'+w+'" height="18" rx="2" fill="'+movementColour(c.change)+'"/></svg><span>'+(c.change===0?'No change':Math.abs(c.change).toFixed(1)+' '+(c.change<0?'fewer':'more')+' trips / 100')+'</span></button>'}).join('')||'<p>More history is needed for a change comparison.</p>';
 function select(name){const c=cats.find(c=>c.name===name),target=document.querySelector('#category-outlook');target.innerHTML='<section class="brand-context"><h2>'+esc(name)+'</h2>'+(c?'<p>'+c.comparable+' comparable buyers'+(c.status==='Insufficient evidence'?' &middot; Limited purchase history':'')+'</p>'+decisionPanel(c)+'<h3>Recorded category trips over time</h3><p class="muted">Monthly shares use the buyers observed that month.</p>'+c.months.map(m=>'<p>'+esc(m.month)+' · '+(m.total?m.trips+' of '+m.total+' trips':'No observed trips')+'</p>').join('')+brandLink(name):'<p>This category has recent buyers, but not enough comparable history for a change analysis.</p>')+'<h3>Follow the evidence</h3>'+report.findings.map((f,i)=>f.label===name?'<p><a class="text-link" href="#evidence/'+i+'">'+esc(f.kind)+' · '+f.buyers+' buyers →</a></p>':'').join('')+'</section>';const download=document.querySelector('#download-brief');if(download)download.onclick=()=>{const url=URL.createObjectURL(new Blob([decisionBrief(c,reportIsExample)],{type:'text/plain;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='category-investigation.txt';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};}
 view.querySelectorAll('[data-name]').forEach(b=>b.onclick=()=>{select(b.dataset.name);document.querySelector('#category-outlook').scrollIntoView({behavior:'smooth',block:'start'})});if(top)select(top.name);
}
function outlook(){
 const items=report.opportunities||[];
 view.innerHTML=intro('Opportunities')+'<div class="bar"><label>Portfolio <select id="portfolio"><option value="pg">P&G</option><option value="all">Whole market context</option></select></label><a href="#brands">Compare brands</a></div><div id="opportunities"></div><div id="opportunity-detail"></div>';
 function draw(){const rows=items.filter(o=>document.querySelector('#portfolio').value==='all'||o.relevant);document.querySelector('#opportunities').innerHTML=rows.map(o=>'<button class="chart-row" data-opportunity="'+o.id+'"><strong>'+esc(o.category)+'</strong><span>'+esc(o.title)+'</span><span>'+o.buyers+' buyers</span></button>').join('')||'<p>No eligible portfolio histories. <a href="#import">Add purchasing history</a></p>';document.querySelector('#opportunity-detail').innerHTML='';view.querySelectorAll('[data-opportunity]').forEach(b=>b.onclick=()=>detail(items.find(o=>o.id===b.dataset.opportunity)));}
 function detail(o){const f=o.forecast;document.querySelector('#opportunity-detail').innerHTML='<section class="panel"><h2>'+esc(o.category)+'</h2><p>'+o.switches+' buyers moved from two P&G category trips to two without P&G.</p>'+(f?'<h3>Next observed category purchase</h3><p><strong>'+f.rate+'%</strong> estimated P&G purchase rate across '+f.buyers+' repeat category buyers.</p>':'<p>More comparable history is needed for a forecast.</p>')+'<details><summary>Evidence</summary><p>'+o.coverage+'% of category item rows belong to receipts with fully recognised brands. Missing receipts and retailer changes can affect observed movement.</p>'+(f?'<p>'+esc(f.method)+' · '+f.validation_buyers+' held-out buyers from '+f.cutoff+'. Brier error '+f.brier.toFixed(3)+'; category baseline '+f.baseline_brier.toFixed(3)+'. Lower is better. This is a single temporal holdout, not a validated intervention effect.</p>':'')+brandLink(o.category)+'</details><h3>Plan a test</h3><div class="bar"><label>Action <select id="test-action"><option>Product-use message</option><option>Targeted offer</option><option>Availability investigation</option></select></label><label>Eligible audience <input id="test-n" type="number" min="1" value="'+o.buyers+'"></label><label>Total cost <input id="test-cost" type="number" min="0" placeholder="Enter cost"></label><label>Net contribution per additional purchaser <input id="test-margin" type="number" min="0" placeholder="Enter contribution"></label></div><p id="economics">Enter cost and contribution in the same currency.</p><button id="export-test" disabled>Create experiment brief</button></section>';
 let brief='';function calculate(){const n=Number(document.querySelector('#test-n').value),cost=Number(document.querySelector('#test-cost').value),margin=Number(document.querySelector('#test-margin').value),valid=Number.isInteger(n)&&n>0&&n<=o.buyers&&Number.isFinite(cost)&&cost>=0&&Number.isFinite(margin)&&margin>0&&document.querySelector('#test-cost').value!=='';document.querySelector('#export-test').disabled=!valid;if(!valid){document.querySelector('#economics').textContent='Enter an audience within the observed cohort, cost and positive net contribution.';return}const extra=Math.ceil(cost/margin),message='Break-even: '+extra+' additional purchasers ('+(100*extra/n).toFixed(1)+' percentage points). '+(extra>n?'Not achievable within this audience.':'Scenario assumptions; uplift is not predicted.');document.querySelector('#economics').textContent=message;brief=[o.category+' — P&G experiment brief','Dataset: '+report.version,'Observation: '+o.switches+' possible portfolio repeat losses.',f?f.target+': '+f.rate+'% (conditional forecast).':'Forecast unavailable.','Action: '+document.querySelector('#test-action').value,'Audience: '+n+'; total cost: '+cost+'; net incremental contribution: '+margin,message,'Compare against no intervention using random allocation within the eligible cohort. Specify follow-up before starting; assess incremental repeat purchasing, contribution after incentives, and observation coverage.','Account for purchases brought forward and movement between P&G brands. Do not claim causal return from receipt associations.'].join('\n\n');}
 view.querySelectorAll('#opportunity-detail input,#test-action').forEach(e=>e.oninput=calculate);document.querySelector('#export-test').onclick=()=>{const url=URL.createObjectURL(new Blob([brief],{type:'text/plain'})),a=document.createElement('a');a.href=url;a.download='experiment-brief.txt';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};
 }
 document.querySelector('#portfolio').onchange=draw;draw();
}
