const $ = (s, root = document) => root.querySelector(s);
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const num = v => Number(v || 0).toLocaleString('en-GB');
const rate = v => `${Math.round((v || 0) * 100)}`;
const date = v => new Date(v).toLocaleDateString('en-GB', {day:'numeric',month:'short',year:'numeric'});
const arrow = '<span aria-hidden="true">→</span>';
const uploadIcon = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M12 16V3m-5 5 5-5 5 5M4 15v5h16v-5"/></svg>';
const state = {report:null, preview:null, sheet:null, busy:false, stage:'', progress:0, error:'', dimension:'category', lens:'all', signal:'all', search:'', customerSearch:'', customerStatus:'all', customerCategory:'all', page:0, dialog:null};
let lastFocus, pollTimer;

async function api(url, options={}) {
  const res = await fetch(url, options);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || 'Something went wrong. Please try again.');
  return data;
}
function post(url, data) {return api(url, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data || {})});}
function notify(message) {const el=$('#toast'); el.textContent=message; el.hidden=false; setTimeout(()=>el.hidden=true,5000);}
function route() {return ['start','data','findings','customers','method'].includes(location.hash.slice(1)) ? location.hash.slice(1) : 'start';}
function badge(text, kind='') {return `<span class="badge ${kind}">${esc(text)}</span>`;}
function metric(title,value,sub) {return `<div class="metric"><label>${esc(title)}</label><strong>${esc(value)}</strong><span>${esc(sub)}</span></div>`;}
function empty(title,body) {return `<div class="empty"><div class="eyebrow">A little data goes a long way</div><h2>${esc(title)}</h2><p>${esc(body)}</p><div class="actions"><a class="btn primary" href="#data">Import receipts ${arrow}</a><button class="btn secondary" data-action="demo">Explore sample data</button></div></div>`;}
function progress() {return state.busy ? `<div class="progress-panel" role="status" aria-live="polite"><h3><span class="spinner"></span>${esc(state.stage || 'Preparing your data')}</h3><p>Your receipts are being checked and connected into customer histories. Larger workbooks can take a minute.</p><div class="track"><div class="fill" style="width:${state.progress}%"></div></div></div>` : '';}
function errorBox() {return state.error ? `<div class="error-box" role="alert"><strong>We need to resolve this first.</strong><br>${esc(state.error)}</div>` : '';}
function header(eyebrow,title,subtitle,action='') {return `<div class="page-head"><div><div class="eyebrow">${eyebrow}</div><h1>${title}</h1><p class="subhead">${subtitle}</p></div>${action}</div>`;}
function context() {
  const r=state.report;
  return `<div class="context-strip"><div>${r.synthetic?'<strong>Sample data.</strong> These findings describe synthetic receipts. ':''}Comparing receipts before and after <strong>${date(r.period.split)}</strong>, using the same customers in both periods. <a href="#method">What this means</a></div></div>`;
}

function startPage() {
  return `<section class="hero"><div><div class="eyebrow">A better question starts with the basket</div><h1>What are your<br>customers <em>telling you?</em></h1><p class="subhead">Turn everyday receipts into a clearer picture of changing habits. Find the patterns worth acting on — and understand the evidence behind them.</p><div class="actions"><a href="#data" class="btn primary">Import your receipts ${arrow}</a><button class="btn secondary" data-action="${state.report?'findings':'demo'}">${state.report?'Continue to findings':'Explore sample data'}</button></div><p class="hero-note">Works with your P&G receipt spreadsheet. No setup or column mapping needed.</p></div>
  <div class="preview-scene" aria-label="Illustrative example of an insight, not a computed finding"><div class="scene-top"><span>FROM RECEIPTS TO RELEVANCE</span><span>ILLUSTRATION</span></div><div class="example-card">${badge('A habit worth understanding','supported')}<h3>Laundry is becoming<br>part of more shopping trips.</h3><p>A useful finding starts with the change, then shows who is behind it.</p><div class="mini-comparison"><div class="mini-line"><span>Earlier</span><div class="track"><div class="fill earlier" style="width:38%"></div></div><b>38</b></div><div class="mini-line"><span>Recent</span><div class="track"><div class="fill" style="width:54%"></div></div><b>54</b></div></div><div class="example-foot">Shopping trips out of every 100 · example only</div></div><div class="scene-tag"><span class="check" aria-hidden="true">✓</span>Every conclusion has a trail back to the receipt.</div></div></section>
  <div class="section-heading"><h2>One clear path from data to insight.</h2><p>Bring the receipts. We’ll help you ask better questions.</p></div>
  <section class="steps"><article class="step"><div class="step-num">01 /</div><h3>Bring your receipt history</h3><p>Upload an Excel workbook. Preview the sheet, check its coverage, then start a new dataset or add more receipts.</p></article><article class="step"><div class="step-num">02 /</div><h3>Find what is changing</h3><p>See purchase routines, emerging activity and possible declines. Clear evidence labels tell you which findings deserve attention.</p></article><article class="step"><div class="step-num">03 /</div><h3>Follow the customer story</h3><p>Explore the people behind a pattern. See when they bought, how consistently they returned and which receipts support the conclusion.</p></article></section>
  <div class="welcome-bottom"><div><h3>Built for commercial questions</h3><p>Where is a routine strengthening? Which customers stopped appearing in a category? Is a brand change worth researching? Focus on all categories or the P&G portfolio’s adjacent needs.</p></div><div><h3>Clear about what receipts can tell you</h3><p>Purchases reveal behaviour, not motivation. We distinguish repeated observations from early signals, with the detailed calculations available when you need them.</p></div></div>${progress()}${errorBox()}`;
}

function dataPage() {
  const r=state.report;
  let html=header('01 / YOUR DATA','The receipts come first.','Upload, check, then explore. Add more history whenever you have it.');
  html+=progress()+errorBox();
  if (!state.preview) {
    html+=`<div class="import-grid"><section class="panel"><label class="dropzone" id="dropzone" for="file-input"><span class="upload-symbol">${uploadIcon}</span><h3>Drop your receipt spreadsheet here</h3><p>One row per item. One ID per receipt.</p><span class="btn primary">Choose a file ${arrow}</span><small>Excel (.xlsx) or CSV · up to 30 MB · 150,000 rows</small></label><input id="file-input" class="visually-hidden" type="file" accept=".xlsx,.csv" ${state.busy?'disabled':''}><div class="divider"></div><div class="section-heading no-margin"><p>Want to see how it works first?</p><button class="quiet" data-action="demo" ${state.busy?'disabled':''}>Use sample receipts ${arrow}</button></div></section>
    <aside class="panel format-guide"><div class="eyebrow">Your existing format</div><h3>A familiar spreadsheet. A new perspective.</h3><p>We recognise the headers in your P&G workbook automatically.</p><div class="field-list">${['Receipt ID','Consumer ID','Date','Product Name'].map(f=>`<span class="field-pill">${f}</span>`).join('')}</div><p>These four columns are required. Customer IDs connect purchases over time; dates let us compare earlier and recent behaviour.</p><details><summary>What else can I include?</summary><p>Store Name, Store Address, Quantity, Unit Price, Line Total, Total Spend, Promotion, Time, Line Number and Image Filename are recognised. Missing optional fields reduce available evidence rather than inventing values.</p></details><a href="/api/template" class="quiet">Download the column template ${arrow}</a><p class="small-muted">Uploads stay in this local browser workspace’s server memory. They are not sent to an AI provider. Reimport after restarting the server.</p></aside></div>`;
  } else {
    const sheet=state.preview.sheets.find(s=>s.name===state.sheet) || state.preview.sheets[0];
    html+=`<section class="panel"><div class="section-heading"><div><div class="eyebrow">PREVIEW YOUR IMPORT</div><h2>${esc(state.preview.filename)}</h2></div><button class="quiet" data-action="cancel-upload">Choose another file</button></div><div class="form-row"><label class="form-field">Worksheet<select id="sheet-select">${state.preview.sheets.map(s=>`<option ${s.name===sheet.name?'selected':''} value="${esc(s.name)}">${esc(s.name)} · ${num(s.rows)} rows</option>`).join('')}</select></label><div>${badge(sheet.ready?'Format recognised':'Needs attention',sheet.ready?'supported':'warning')}</div></div>
    ${sheet.missing.length?`<div class="error-box">Add these required columns before importing: <strong>${sheet.missing.map(esc).join(', ')}</strong>.</div>`:''}
    <div class="preview-table"><table><thead><tr>${sheet.columns.map(c=>`<th>${esc(c)}</th>`).join('')}</tr></thead><tbody>${sheet.sample.map(row=>`<tr>${sheet.columns.map(c=>`<td>${esc(row[c])}</td>`).join('')}</tr>`).join('')}</tbody></table></div>
    ${r?`<h3>How should we use these receipts?</h3><div class="radio-options"><label class="radio-option"><input type="radio" name="import-mode" value="append" checked><span>Add to this dataset<p>Combine histories using customer and receipt IDs. Identical receipts are skipped; conflicting receipts are stopped for review.</p></span></label><label class="radio-option"><input type="radio" name="import-mode" value="replace"><span>Start a separate dataset<p>Replace this browser’s analysis with this file. Your original workbook is never edited.</p></span></label></div>`:''}
    <label class="checkbox-label"><input type="checkbox" id="synthetic-check" ${r?.synthetic?'checked':''}>This workbook contains synthetic or demonstration data</label><div class="actions"><button class="btn primary" data-action="import" ${!sheet.ready||state.busy?'disabled':''}>Analyse ${num(sheet.rows)} rows ${arrow}</button><span class="small-muted">We’ll check the data before making any changes.</span></div></section>`;
  }
  if(r) html+=`<section class="source-list"><div class="section-heading"><h2>In this workspace</h2><a class="quiet" href="#findings">View findings ${arrow}</a></div>${r.sources.map(s=>`<div class="source-item"><div><strong>${esc(s.name)}</strong><p>${esc(s.sheet)} · ${num(s.rows)} supplied rows · ${num(s.receipts)} supplied receipts</p></div>${badge('Analysed','supported')}</div>`).join('')}<p class="small-muted">The combined dataset contains ${num(r.totals.receipts)} distinct receipts. Imported source counts can overlap.</p></section>`;
  return html;
}

function compare(i,large=false) {
  return `<div class="comparison ${large?'big-comparison':''}"><div class="mini-line"><span>Earlier</span><div class="track"><div class="fill earlier" style="width:${rate(i.earlier)}%"></div></div><strong>${rate(i.earlier)} in 100</strong></div><div class="mini-line" style="margin-top:14px"><span>Recent</span><div class="track"><div class="fill" style="width:${rate(i.recent)}%"></div></div><strong>${rate(i.recent)} in 100</strong></div><div class="comparison-caption">Shopping trips containing this category · average across the same customers</div></div>`;
}
function findingsPage() {
  const r=state.report;
  if(!r) return header('02 / FINDINGS','The useful patterns, brought forward.','Conclusions first. Evidence whenever you need it.')+progress()+empty('Your findings start with receipts.','Import a workbook to see the routines and changes in your customers’ observed purchases.');
  let view=r.insights.filter(i=>i.dimension===state.dimension && (state.lens==='all'||i.adjacent) && (state.signal==='all'||i.signal===state.signal) && i.name.toLowerCase().includes(state.search.toLowerCase()));
  return header('02 / FINDINGS','What deserves your attention?','Explore changes in customer behaviour, then follow the evidence to a practical next question.',`<a class="btn secondary" href="/api/export">Download findings ${arrow}</a>`)+
    `<div class="metric-row">${metric('Customers observed',num(r.totals.customers),'Across all imported receipts')}${metric('Comparable histories',num(r.totals.comparable),'At least 3 receipts in each period')}${metric('Supported category changes',num(r.totals.supported),'Direction passes the evidence checks')}${metric('Purchase categories',num(r.totals.categories),`${num(r.totals.functions)} more specific purchase functions`)}</div>`+context()+
    `<div class="filterbar"><div class="segmented" role="group" aria-label="Analysis level"><button data-action="dimension" data-value="category" class="${state.dimension==='category'?'selected':''}">Categories</button><button data-action="dimension" data-value="function" class="${state.dimension==='function'?'selected':''}">Specific needs</button></div><select id="lens" aria-label="Portfolio focus"><option value="all">Whole market</option><option value="portfolio" ${state.lens==='portfolio'?'selected':''}>P&G adjacent</option></select><select id="signal" aria-label="Finding type"><option value="all">All findings</option><option value="supported" ${state.signal==='supported'?'selected':''}>Supported changes</option><option value="watch" ${state.signal==='watch'?'selected':''}>Worth watching</option><option value="routine" ${state.signal==='routine'?'selected':''}>Repeated routines</option></select><input id="finding-search" class="search" placeholder="Find a category…" aria-label="Search categories" value="${esc(state.search)}"><span class="results-count">${view.length} findings</span></div>
    ${state.dimension==='function'?'<p class="small-muted" style="margin-bottom:20px">Specific needs group products by their function, such as fabric care or dishwashing. They describe what products do, not a customer’s private motivations.</p>':''}
    ${view.length?`<section class="insight-grid">${view.map(i=>`<article class="insight"><div class="card-top">${badge(i.confidence,i.signal)}<span class="category-tag">${i.adjacent?'P&G adjacent':esc(i.name)}</span></div><h3>${esc(i.headline)}</h3><p class="description">${esc(i.conclusion)}</p>${compare(i)}<div class="card-takeaway"><strong>Why look closer?</strong> ${esc(shortTakeaway(i))}</div><div class="card-bottom"><span>${num(i.buyers)} customers bought here</span><button class="quiet" data-action="insight" data-id="${esc(i.id)}">Understand this finding ${arrow}</button></div></article>`).join('')}</section>`:`<div class="empty"><h2>${r.totals.comparable?'No findings match these filters.':'More history is needed.'}</h2><p>${r.totals.comparable?'Try a different view or broaden the business focus.':'Customers need at least three observed receipts before and after the midpoint. You can still explore their observed purchases.'}</p><a class="btn secondary" href="#customers">Explore customers ${arrow}</a></div>`}
    <div class="welcome-bottom"><div><h3>What does “supported” mean?</h3><p>The direction is consistent across enough customers and passes our uncertainty checks. It still needs business context before action.</p></div><div><h3>Why some findings say “worth watching”</h3><p>The observed change is interesting, but there is not enough consistent evidence to treat it as a lasting shift. <a href="#method" class="quiet">See how decisions work ${arrow}</a></p></div></div>`;
}
function shortTakeaway(i) {
  if(i.states['Newly observed']) return `${i.states['Newly observed']} customers bought here repeatedly in the recent period after no earlier observations.`;
  if(i.states['No longer observed']) return `${i.states['No longer observed']} earlier repeat buyers have no recent purchases in these receipts.`;
  if(i.repeat_buyers) return `${i.repeat_buyers} customers returned to this purchase area. Their habits are a starting point for research.`;
  return 'This is an early observation. More repeated purchases will help establish whether a routine exists.';
}

function customersPage() {
  const r=state.report;
  if(!r) return header('03 / CUSTOMERS','The people behind the pattern.','Follow purchases over time, without guessing why someone bought.')+empty('Connect receipts into customer stories.','Customer IDs let us see repeated behaviour and how it changes.');
  const cats=r.insights.filter(i=>i.dimension==='category');
  let customers=r.customers.filter(c=>c.id.toLowerCase().includes(state.customerSearch.toLowerCase()));
  if(state.customerCategory!=='all') customers=customers.filter(c=>c.patterns.some(p=>p.entity===state.customerCategory));
  if(state.customerInsight) customers=customers.filter(c=>state.customerInsight.customer_ids.includes(c.id));
  if(state.customerStatus!=='all') customers=customers.filter(c=>c.patterns.some(p=>(state.customerCategory==='all'||p.entity===state.customerCategory)&&p.status===state.customerStatus));
  customers.sort((a,b)=>b.changes-a.changes || b.score-a.score);
  const pageCount=Math.max(1,Math.ceil(customers.length/15));state.page=Math.min(state.page,pageCount-1);
  const page=customers.slice(state.page*15,(state.page+1)*15);
  return header('03 / CUSTOMERS','Follow the customer story.','See what was bought, what changed, and how much history supports the interpretation.')+
    (state.customerInsight?`<div class="context-strip"><div>Showing comparable buyers behind <strong>${esc(state.customerInsight.name)}</strong>. <button class="quiet" data-action="clear-customer-insight">Show all customers</button></div></div>`:'')+
    `<div class="context-strip"><div>Customer labels describe purchases seen in this dataset. “No longer observed” does not mean the customer stopped buying elsewhere. <a href="#method">Read the interpretation guide</a></div></div>
    <div class="filterbar"><input id="customer-search" class="search" placeholder="Search customer ID…" aria-label="Search customer ID" value="${esc(state.customerSearch)}"><select id="customer-category" aria-label="Customer category"><option value="all">All purchase categories</option>${cats.map(c=>`<option value="${esc(c.entity)}" ${state.customerCategory===c.entity?'selected':''}>${esc(c.name)}</option>`).join('')}</select><select id="customer-status" aria-label="Customer behaviour"><option value="all">All observed behaviours</option>${['Newly observed','No longer observed','Buying more often','Buying less often','Established routine','Occasional purchase','Not enough history'].map(s=>`<option ${state.customerStatus===s?'selected':''}>${esc(s)}</option>`).join('')}</select><span class="results-count">${num(customers.length)} customers</span></div>
    <div class="table-wrap"><table><thead><tr><th>Customer</th><th>Receipts</th><th>What stands out</th><th>History coverage</th><th></th></tr></thead><tbody>${page.map(c=>`<tr><td><button class="quiet customer-id" data-action="customer" data-id="${esc(c.id)}">${esc(c.id)}</button></td><td>${c.receipts}<br><small class="small-muted">${c.earlier} earlier · ${c.recent} recent</small></td><td><strong>${esc(customerHeadline(c))}</strong><br><small class="small-muted">${c.days} days observed</small></td><td><div class="score-line"><div class="track"><div class="fill" style="width:${c.score}%"></div></div><span>${esc(c.evidence)}</span></div></td><td><button class="quiet" data-action="customer" data-id="${esc(c.id)}" aria-label="Explore customer ${esc(c.id)}">${arrow}</button></td></tr>`).join('') || '<tr><td colspan="5">No customers match. Try broadening the filters.</td></tr>'}</tbody></table></div><div class="pagination"><span>Page ${state.page+1} of ${pageCount}</span><div class="actions"><button class="btn secondary" data-action="previous" ${state.page===0?'disabled':''}>Previous</button><button class="btn secondary" data-action="next" ${state.page>=pageCount-1?'disabled':''}>Next</button></div></div>
    ${r.brand_shifts.length?`<section class="panel" style="margin-top:30px"><div class="eyebrow">A MORE SPECIFIC QUESTION</div><h2>Some customers changed their leading brand.</h2><p class="subhead">${num(new Set(r.brand_shifts.map(s=>s.customer)).size)} customers have a different most-purchased brand within a category. Both periods include repeated purchases; this is a reason to investigate, not proof of substitution.</p><button class="quiet" data-action="brands">Explore brand changes ${arrow}</button></section>`:''}`;
}
function customerHeadline(c) {
  if(!c.eligible) return 'More receipts needed for a comparison';
  const p=c.patterns.find(p=>['Newly observed','No longer observed','Buying more often','Buying less often'].includes(p.status)) || c.patterns.find(p=>p.status==='Established routine') || c.patterns[0];
  return p ? `${p.name} · ${p.status.toLowerCase()}` : 'No classified purchases';
}
function methodPage() {
  return header('THE EVIDENCE GUIDE','Clear conclusions. Visible reasoning.','You should understand a finding before you need to understand its statistics.')+
  `<section class="method-grid"><article class="panel"><div class="step-num">01 /</div><h3>We connect receipts into histories</h3><p>Customer IDs connect shopping trips. Product descriptions are resolved into families, purchase categories and more specific functions. Unrecognised products remain visible as unclassified.</p></article><article class="panel"><div class="step-num">02 /</div><h3>We compare like with like</h3><p>The observation window is split in half. We compare the same customers in both halves, counting how often a category appears in their shopping trips. A frequent shopper does not outweigh everyone else.</p></article><article class="panel"><div class="step-num">03 /</div><h3>We distinguish a signal from a story</h3><p>Repeated purchases can establish an observed routine. A population change needs enough buyers, consistent direction and an uncertainty check. Neither tells us a person’s private motivation.</p></article><article class="panel"><div class="step-num">04 /</div><h3>We make the next question practical</h3><p>Investigate availability, timing, basket size and retailer coverage before designing a commercial experiment. New activity or an absent purchase is a clue, not proof of adoption or churn.</p></article>
  <article class="panel method-full"><h3>Reading the findings</h3><div class="breakdown"><div>${badge('Supported change','supported')}<p class="small-muted" style="margin-top:12px">Passes the population evidence checks. Still needs context and replication.</p></div><div>${badge('Worth watching','watch')}<p class="small-muted" style="margin-top:12px">A visible change without enough consistent evidence for a firm conclusion.</p></div><div>${badge('Descriptive pattern','routine')}<p class="small-muted" style="margin-top:12px">A description of observed purchases, not a claim that behaviour is changing.</p></div></div>
  <details><summary>How is customer history rated?</summary><p>“Well observed” means quality receipts and balanced, sustained observation. “Limited history” means a comparison could be driven by a few shopping trips. The rating is an evidence score, not the probability that a prediction is correct.</p><p>Calculation: mean receipt quality × smaller period receipt count / 5 (capped at 1) × days observed / 90 (capped at 1), scaled to 100. Well observed: 80 or above; some history: 50–79; limited: below 50. These thresholds are heuristic and not calibrated.</p></details>
  <details><summary>How are individual behaviours assigned?</summary><p>Comparisons require at least three receipts in each period. Newly observed: at least two recent purchases and none earlier. No longer observed: at least two earlier purchases and none recently. More/less often: at least a 25 percentage-point change with three supporting purchases. An established routine appears on at least half the trips in both periods. These are descriptive review signals.</p></details>
  <details><summary>What statistical checks support a population change?</summary><p>We require at least 20 comparable customers and 10 buyers. A paired sign test asks whether customers tend to move in the same direction. Benjamini–Hochberg correction accounts for testing several categories (or functions) together; the corrected value must be below 0.05. A 95% interval from 1,000 customer bootstrap samples must also exclude zero and agree in direction. The sign test concerns directional consistency, while the interval concerns mean frequency change.</p><p>The two views have separate correction families; exploring both does not create one universal false-discovery guarantee. Neither test is causal. Brand and individual behaviour labels are descriptive, not separately significance-tested predictions.</p></details>
  <details><summary>What is the difference between percent and percentage points?</summary><p>If a category appears in 40 of every 100 trips earlier and 50 recently, that is 10 additional trips per 100 — a rise of 10 percentage points. Relative growth would be 25%. We use “trips out of 100” in the findings so the comparison is direct.</p></details>
  <details><summary>What could explain a change besides customer demand?</summary><p>Seasonality, retailer assortment, promotion, changing basket sizes and missing receipts can all matter. We show item-share and stable-retailer sensitivity checks where available, but they do not remove all confounding. With less than two years, seasonal and emerging effects remain unresolved.</p><p>Synthetic results test the analytical workflow, not real demand. We do not infer medical conditions, household composition or other sensitive personal attributes.</p></details></article></section>`;
}

function render() {
  const active=route();
  document.querySelectorAll('#nav a').forEach(a=>{a.classList.toggle('active',a.dataset.route===active); if(a.dataset.route===active)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');});
  $('#breadcrumb').innerHTML=`Workspace <span>/</span> ${{start:'Start here',data:'Receipt data',findings:'Findings',customers:'Customers',method:'Evidence guide'}[active]}`;
  $('#dataset-status').textContent=state.report?`${num(state.report.totals.receipts)} receipts · ${state.report.synthetic?'sample dataset':'your dataset'}`:'No dataset yet';
  $('#main').innerHTML=({start:startPage,data:dataPage,findings:findingsPage,customers:customersPage,method:methodPage}[active])();
  bindDropzone();
}

function showDialog(content,kind,id) {
  if(!state.dialog) lastFocus=document.activeElement;
  state.dialog={kind,id};
  $('#dialog-root').innerHTML=`<div class="overlay" data-action="overlay-close"><section class="drawer" role="dialog" aria-modal="true" aria-label="${kind==='customer'?'Customer details':'Finding details'}" tabindex="-1"><div class="drawer-close"><span>${kind==='customer'?'Customer evidence':'Behind the finding'}</span><button class="icon-btn" data-action="close" aria-label="Close details">×</button></div>${content}</section></div>`;
  document.body.style.overflow='hidden'; $('.drawer').focus();
}
function closeDialog() {$('#dialog-root').innerHTML='';state.dialog=null;document.body.style.overflow='';lastFocus?.focus();}
function insightDialog(id) {
  const i=state.report.insights.find(i=>i.id===id);if(!i)return;
  const changed=Math.abs(i.change*100).toFixed(1);
  showDialog(`${badge(i.confidence,i.signal)}<h2>${esc(i.headline)}</h2><p class="drawer-lead">${esc(i.conclusion)}</p>${compare(i,true)}
  <div class="drawer-section"><h3>Who is behind the change?</h3><p>These counts describe customers with comparable histories in both periods.</p><div class="breakdown"><div><strong>${i.states['Newly observed']||0}</strong><span>Newly observed buyers</span></div><div><strong>${i.states['No longer observed']||0}</strong><span>No recent purchases</span></div><div><strong>${i.states['Established routine']||0}</strong><span>Established routines</span></div></div><button class="quiet" data-action="show-customers" data-id="${esc(i.id)}">Explore the customers ${arrow}</button></div>
  <div class="action-box"><div class="eyebrow">NEXT QUESTION TO INVESTIGATE</div><p>${esc(i.action)}</p></div>
  <div class="drawer-section"><h3>Keep this context in mind</h3><ul class="caution-list">${i.cautions.map(c=>`<li>${esc(c)}</li>`).join('')}<li>Repeated activity does not reveal why someone bought. Missing activity may reflect shops outside this dataset.</li></ul></div>
  <div class="drawer-section"><h3>How the observation developed</h3>${trendChart(i.monthly)}<p class="chart-caption">Average purchase frequency among customers observed each month. Monthly customers can differ; the headline comparison uses the same customers.</p></div>
  <details><summary>See the statistical evidence</summary><p>The observed change is about <strong>${changed} ${i.change>0?'more':'fewer'} shopping trips out of every 100</strong>. Here is how we assess uncertainty around it.</p><div class="stat-detail"><div><label>Range consistent with resampled customers</label><strong>${(i.low*100).toFixed(1)} to ${(i.high*100).toFixed(1)}</strong><p>Additional trips per 100. A range crossing zero means the average could reasonably move either way.</p></div><div><label>Corrected directional test</label><strong>${i.q.toFixed(4)}</strong><p>Below 0.05 passes this check. This is not the chance the insight is wrong.</p></div></div><p>${i.up} customers increased, ${i.down} decreased and ${i.unchanged} were unchanged. ${i.customers} were comparable in total, including non-buyers. Tests across the ${i.dimension} view are corrected together.</p><p>Among ${i.stable_retailer_customers} customers with unchanged retailer coverage, the average change was ${i.stable_retailer_change===null?'unavailable':(100*i.stable_retailer_change).toFixed(1)+' additional trips per 100'}. Category share of basket items changed by ${(i.item_share_change*100).toFixed(1)} percentage points. These are sensitivity checks, not causal adjustments.</p></details>
  <details><summary>Products supporting this purchase area</summary><ul class="receipt-products">${i.products.map(p=>`<li><span>${esc(p.name)}</span><small>${num(p.receipts)} receipts</small></li>`).join('')}</ul></details>`, 'insight',id);
}
function trendChart(points) {
  if(points.length<2)return '<p class="small-muted">More than one month is needed for a timeline.</p>';
  const w=540,h=170,pad=28,max=Math.max(.1,...points.map(p=>p.rate));
  const xx=k=>pad+k*(w-pad*2)/(points.length-1), yy=v=>h-pad-v/max*(h-pad*2);
  const path=points.map((p,k)=>`${k?'L':'M'}${xx(k)},${yy(p.rate)}`).join(' ');
  return `<div class="trend-chart"><svg viewBox="0 0 ${w} ${h}" role="img" aria-label="Monthly observed purchase frequency"><line x1="${pad}" y1="${h-pad}" x2="${w-pad}" y2="${h-pad}" stroke="#dce5d5"/><path d="${path}" fill="none" stroke="#1b6654" stroke-width="2.5"/>${points.map((p,k)=>`<circle cx="${xx(k)}" cy="${yy(p.rate)}" r="4" fill="#1b6654"><title>${esc(p.month)}: ${rate(p.rate)} in 100 trips; ${p.customers} customers</title></circle><text x="${xx(k)}" y="${yy(p.rate)-12}" text-anchor="middle" font-size="10" fill="#35533d">${rate(p.rate)}%</text>${points.length<=12||k===0||k===points.length-1?`<text x="${xx(k)}" y="${h-5}" text-anchor="middle" font-size="9" fill="#7d8d77">${esc(p.month.slice(2))}</text>`:''}`).join('')}</svg></div>`;
}
function customerDialog(id) {
  const c=state.report.customers.find(c=>c.id===id);if(!c)return;
  const receipts=state.report.receipts[id] || [];
  const shifts=state.report.brand_shifts.filter(s=>s.customer===id);
  showDialog(`<div class="eyebrow">${esc(c.evidence)}</div><h2>Customer ${esc(c.id)}</h2><p class="drawer-lead">${esc(customerHeadline(c))}. This history covers ${c.receipts} receipts over ${c.days} days.</p>
  <div class="breakdown"><div><strong>${c.earlier}</strong><span>Earlier receipts</span></div><div><strong>${c.recent}</strong><span>Recent receipts</span></div><div><strong>${c.cadence_days===null?'—':Math.round(c.cadence_days)}</strong><span>Median days between trips</span></div></div>
  ${!c.eligible?'<div class="context-strip">There are fewer than three receipts in one period. Purchases are shown below, but this history cannot support a change comparison.</div>':''}
  <div class="drawer-section"><h3>Observed routines</h3><div class="pattern-list">${c.patterns.map(p=>`<div class="pattern-item"><div class="pattern-top"><strong>${esc(p.name)}</strong>${badge(p.status,p.status==='Established routine'?'supported':'')}</div><p>${p.earlier} of ${p.n_earlier} earlier trips → ${p.recent} of ${p.n_recent} recent trips.</p></div>`).join('') || '<p>No purchases could be classified. Review the source product names.</p>'}</div></div>
  ${shifts.length?`<div class="drawer-section"><h3>A change in leading brand</h3>${shifts.map(s=>`<div class="pattern-item"><strong>${esc(s.category)}</strong><p>${esc(s.earlier)} (${s.earlier_receipts} receipts) → ${esc(s.recent)} (${s.recent_receipts} receipts).</p></div>`).join('')}<p class="chart-caption">Both brands were observed repeatedly. This does not establish substitution or exclusive loyalty.</p></div>`:''}
  <details><summary>Why is this history rated “${esc(c.evidence.toLowerCase())}”?</summary><p>We rate the strength of observation, not whether we know the customer’s motivation.</p><div class="stat-detail"><div><label>Receipt quality</label><strong>${c.quality}/100</strong><p>Readable products, prices and arithmetic checks.</p></div><div><label>Balanced coverage</label><strong>${c.coverage}/100</strong><p>Full coverage at five receipts in each period.</p></div><div><label>Observation duration</label><strong>${c.duration}/100</strong><p>Full duration credit at 90 days.</p></div><div><label>Combined history evidence</label><strong>${c.score}/100</strong><p>The three factors are multiplied. This score is heuristic, not a calibrated probability.</p></div></div>${c.retailer_changed?'<p>Retailer coverage changed between periods, which may explain some differences in the basket.</p>':''}</details>
  <div class="drawer-section"><h3>Receipt timeline</h3><p>Open any trip to inspect the purchased items.</p>${receipts.map((r,index)=>`<div class="receipt-row"><span class="receipt-date">${date(r.date)}</span><span class="receipt-dot ${r.period==='Recent'?'present':''}"></span><span><strong>${esc(r.retailer)}</strong><br><small>${r.products.length} items · ${esc(r.period.toLowerCase())} period</small></span><button data-action="receipt" data-id="${esc(id)}" data-index="${index}">View receipt ${arrow}</button></div>`).join('')}</div>`, 'customer',id);
}
function receiptDialog(cid,index) {
  const r=state.report.receipts[cid]?.[index];if(!r)return;
  showDialog(`<button class="back-link" data-action="customer" data-id="${esc(cid)}">← Back to customer</button><div class="eyebrow">OBSERVED PURCHASES</div><h2>${esc(r.retailer)}</h2><p class="drawer-lead">${date(r.date)} · ${esc(r.id)}</p><ul class="receipt-products">${r.products.map(p=>`<li><span>${esc(p.name)}<small>${esc(p.category)}${p.quantity!==null?' · quantity '+esc(p.quantity):''}</small></span><span>${p.total===null?'—':'£'+Number(p.total).toFixed(2)}</span></li>`).join('')}</ul><p class="small-muted" style="margin-top:20px">Receipt quality: ${r.quality}/100. All items above came from the source data; none were inferred or reconstructed. Currency display follows the supplied UK receipt format.</p>`, 'receipt',cid);
}
function brandsDialog() {
  showDialog(`<div class="eyebrow">DESCRIPTIVE BRAND MOVEMENTS</div><h2>A different brand leads the recent basket.</h2><p class="drawer-lead">A customer’s most frequently purchased brand changed within a category. We require at least two receipts supporting each leading brand and exclude tied leaders.</p><p class="small-muted">These observations are not proof of switching, loyalty or causal preference change.</p><div class="pattern-list" style="margin-top:24px">${state.report.brand_shifts.slice(0,100).map(s=>`<div class="pattern-item"><div class="pattern-top"><strong>${esc(s.category)}</strong><button class="quiet" data-action="customer" data-id="${esc(s.customer)}">${esc(s.customer)} ${arrow}</button></div><p>${esc(s.earlier)} → ${esc(s.recent)}</p><p>${s.earlier_receipts} earlier receipts · ${s.recent_receipts} recent receipts</p></div>`).join('')}</div>${state.report.brand_shifts.length>100?'<p class="small-muted">Showing the first 100 observations. Individual customer details include their full brand observations.</p>':''}`, 'brands','');
}

async function uploadFile(file) {
  if(!file||state.busy)return;
  if(file.size>30*1024*1024){state.error='Choose a file smaller than 30 MB.';render();return;}
  state.error='';state.busy=true;state.stage='Reading workbook and recognising columns';state.progress=15;render();
  try {const form=new FormData();form.append('file',file);state.preview=await api('/api/upload',{method:'POST',body:form});state.sheet=state.preview.sheets.find(s=>s.ready)?.name || state.preview.sheets[0]?.name;}
  catch(e){state.error=e.message;}
  finally{state.busy=false;render();}
}
function bindDropzone() {
  const zone=$('#dropzone');if(!zone)return;
  zone.addEventListener('dragover',e=>{e.preventDefault();zone.classList.add('drag');});
  zone.addEventListener('dragleave',()=>zone.classList.remove('drag'));
  zone.addEventListener('drop',e=>{e.preventDefault();zone.classList.remove('drag');uploadFile(e.dataTransfer.files[0]);});
}
async function begin(url,body={}) {
  if(state.busy)return;
  state.error='';state.busy=true;state.stage='Checking receipt data';state.progress=10;render();
  try{await post(url,body);poll();}catch(e){state.busy=false;state.error=e.message;render();}
}
async function poll() {
  clearTimeout(pollTimer);
  try {
    const data=await api('/api/state?job=1');const job=data.job;
    if(job?.status==='running'){state.busy=true;state.stage=job.stage;state.progress=job.progress;render();pollTimer=setTimeout(poll,1500);}
    else if(job?.status==='complete') {
      const full=await api('/api/state');state.report=full.report;state.busy=false;state.preview=null;state.search='';state.signal='all';state.page=0;state.customerInsight=null;state.customerCategory='all';
      location.hash='findings';render();notify(`Ready: ${num(state.report.totals.receipts)} distinct receipts analysed${state.report.import_result.skipped_receipts?`; ${state.report.import_result.skipped_receipts} already-imported receipts skipped`:''}.`);
    } else {state.busy=false;state.error=job?.message||'Import did not finish. Please try again.';render();}
  }catch(e){state.busy=false;state.error=e.message;render();}
}
document.addEventListener('click',e=>{
  const button=e.target.closest('[data-action]');if(!button)return;
  const action=button.dataset.action,id=button.dataset.id;
  if(action==='overlay-close'){if(e.target===button)closeDialog();return;}
  if(action==='close')return closeDialog();
  if(action==='demo') {location.hash='data';return begin('/api/demo');}
  if(action==='findings'){location.hash='findings';return;}
  if(action==='cancel-upload'){state.preview=null;state.error='';render();return;}
  if(action==='import')return begin('/api/import',{sheet:state.sheet,mode:$('input[name="import-mode"]:checked')?.value||'replace',synthetic:$('#synthetic-check').checked});
  if(action==='dimension'){state.dimension=button.dataset.value;render();return;}
  if(action==='insight')return insightDialog(id);
  if(action==='customer')return customerDialog(id);
  if(action==='receipt')return receiptDialog(id,Number(button.dataset.index));
  if(action==='brands')return brandsDialog();
  if(action==='clear-customer-insight'){state.customerInsight=null;state.customerCategory='all';state.page=0;render();return;}
  if(action==='show-customers') {
    const i=state.report.insights.find(i=>i.id===id);state.customerInsight=i;state.customerCategory=i.dimension==='category'?i.entity:'all';state.customerStatus='all';state.customerSearch='';state.page=0;closeDialog();location.hash='customers';render();return;
  }
  if(action==='next'||action==='previous'){state.page+=action==='next'?1:-1;render();}
});
document.addEventListener('change',e=>{
  if(e.target.id==='file-input')return uploadFile(e.target.files[0]);
  const map={'sheet-select':'sheet',lens:'lens',signal:'signal','customer-category':'customerCategory','customer-status':'customerStatus'};
  if(map[e.target.id]){state[map[e.target.id]]=e.target.value;state.page=0;render();}
});
let searchTimer;
document.addEventListener('input',e=>{
  const key={'finding-search':'search','customer-search':'customerSearch'}[e.target.id];if(!key)return;
  state[key]=e.target.value;state.page=0;const id=e.target.id,position=e.target.selectionStart;
  clearTimeout(searchTimer);searchTimer=setTimeout(()=>{render();const el=$('#'+id);el?.focus();el?.setSelectionRange(position,position);},180);
});
document.addEventListener('keydown',e=>{
  if(!state.dialog)return;
  if(e.key==='Escape')closeDialog();
  if(e.key==='Tab'){
    const nodes=[...$('.drawer').querySelectorAll('button,a,input,select,summary,[tabindex="0"]')].filter(el=>el.getClientRects().length);
    if(!nodes.length)return;
    if(e.shiftKey&&(document.activeElement===nodes[0]||document.activeElement===$('.drawer'))){e.preventDefault();nodes.at(-1).focus();}
    else if(!e.shiftKey&&document.activeElement===nodes.at(-1)){e.preventDefault();nodes[0].focus();}
  }
});
window.addEventListener('hashchange',()=>{closeDialog();render();window.scrollTo(0,0);});
render();
try {const data=await api('/api/state');state.report=data.report;if(data.job?.status==='running'){state.busy=true;poll();}render();}catch(e){state.error=e.message;render();}
