const view=document.querySelector('#view'), notice=document.querySelector('#notice');
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const btn=(href,title)=>'<a class="btn" href="#'+href+'">'+title+'</a>';
const intro=(step,title,copy)=>'<p class="eyebrow">'+step+'</p><h1>'+title+'</h1><p class="lead">'+copy+'</p>';
let report,filter='All findings',query='',token,epoch=0;
async function api(url,opts){const r=await fetch('/api/'+url,opts),v=await r.json();if(!r.ok)throw Error(v.error||'Could not load the workspace.');return v}
const diagram='<svg class="graphic" viewBox="0 0 280 210" aria-hidden="true"><g fill="none" stroke="var(--on-aubergine-mute)" stroke-width="1.2"><path d="M25 46L90 67L142 100L224 50M25 100L90 67M25 150L88 148L142 100L224 153M25 190L88 148M142 100L245 100"/><circle cx="142" cy="100" r="32" stroke-dasharray="3 6"/></g><g fill="var(--on-aubergine-mute)"><circle cx="25" cy="46" r="6"/><circle cx="25" cy="100" r="6"/><circle cx="25" cy="150" r="6"/><circle cx="25" cy="190" r="6"/><circle cx="90" cy="67" r="11"/><circle cx="88" cy="148" r="11"/></g><g fill="var(--on-primary)"><circle cx="142" cy="100" r="19"/><circle cx="224" cy="50" r="9"/><circle cx="245" cy="100" r="7"/><circle cx="224" cy="153" r="10"/></g></svg>';
function start(){view.innerHTML='<p class="eyebrow">WORKSPACE / START</p><section class="hero"><div><p class="eyebrow">RECEIPT INTELLIGENCE</p><h1>What brought shoppers to the basket?</h1><p>See which needs a shop might serve, which purchases repeat, and what changed for individual buyers.</p><div class="actions">'+btn('import','Import receipts →')+'<button class="secondary" id="example">Explore example</button></div></div>'+diagram+'</section><h2 class="section">How to read a shop</h2><div class="grid">'+[['01','Bring your receipts','Upload an Excel workbook with one row per item. Matching receipts are counted once.'],['02','Read the findings','See shopping missions: groups of products that suggest a purpose, such as restocking laundry supplies. One shop can serve several needs.'],['03','Follow the evidence','Open a finding to see the buyers and receipts behind it. Expand the evidence to see how certain the interpretation is.']].map(([n,t,c])=>'<article class="card"><span class="num">'+n+'</span><h3>'+t+'</h3><p>'+c+'</p></article>').join('')+'</div>';document.querySelector('#example').onclick=()=>submit(null)}
function importPage(s){
    view.innerHTML=intro('IMPORT','Import receipts','Choose an Excel workbook to analyse. Each file starts a fresh analysis.')
        +'<section class="upload"><p>Use one row per item, with Receipt ID, Product Name and Date. Include Consumer ID to see buyer histories.</p>'
        +'<p>Use synthetic receipts only. Do not upload real shoppers’ receipts or personal information. For longer histories, include all periods in one cumulative workbook. Imports replace the current analysis.</p><label><input id="data-scope" type="checkbox"> I confirm this workbook contains synthetic data.</label><input hidden type="file" id="file" accept=".xlsx"><div class="bar"><button type="button" id="choose">Add a file</button><small>.xlsx · Up to 16 MB</small></div></section><div id="feedback" role="status"></div>';
    const file=view.querySelector('#file'), choose=view.querySelector('#choose');
    choose.onclick=()=>{if(!view.querySelector('#data-scope').checked){feedback('Confirm the synthetic data declaration first.');return}file.click()};
    file.onchange=async()=>{
        const selected=file.files[0];
        if(!selected)return;
        choose.disabled=true;
        view.querySelector('#feedback').textContent='';
        try{await submit(selected)}finally{file.value='';choose.disabled=false}
    };
    if(s.phase==='error')feedback(s.error);
    if(s.phase==='working'){choose.disabled=true;waiting().finally(()=>choose.disabled=false)}
}
function feedback(msg){const el=document.querySelector('#feedback')||view.appendChild(document.createElement('p'));el.className='error';el.textContent=msg}
async function waiting(){notice.textContent='Reading receipts and checking findings…';for(;;){await new Promise(r=>setTimeout(r,650));const s=await api('state');if(s.phase==='working'){notice.textContent=s.stage||'Analysing receipts…';continue;}notice.textContent='';if(s.phase==='error'){feedback(s.error);return}report=null;filter='All findings';query='';if(location.hash==='#outlook')await route();else location.hash='outlook';return}}
async function submit(file){try{await api(file?'import':'sample',{method:'POST',headers:{'X-Workspace':token,'X-Data-Scope':'synthetic'},body:file||null});await waiting()}catch(e){notice.textContent='';feedback(e.message)}}
const descriptions={'Shopping mission':'The products bought together suggest this need.','Mixed basket':'Each counted receipt supports at least two distinct needs, such as breakfast and laundry.','Newly observed':'These buyers first bought this category from the comparison date onward.','No recent purchase':'These buyers kept shopping, but this category disappeared from their recorded receipts.','More frequent':'This category appeared on a larger share of these buyers’ trips after the dataset midpoint compared with before it.','Less frequent':'This category appeared on a smaller share of these buyers’ trips after the dataset midpoint compared with before it.','Established routine':'These buyers repeatedly bought this category before and after the split date.','Occasional purchase':'These buyers bought this category before and after the split date without a strong routine or frequency shift.','Limited history':'There are too few trips on one side of the comparison date to judge a change.'};
function empty(){view.innerHTML=intro('WORKSPACE','Start with receipts','Import a workbook or try the example to see findings and their supporting receipts.')+btn('import','Go to import')+' <a class="back" href="#start">Explore the example</a>'}
function missionText(f){
    return f.inference?.replace(/On 0 of these,.+$/, 'The suggestion comes from what the products are used for.') ||
        'The products on these trips serve '+f.label.toLowerCase()+'.';
}
function ranges(){
    const boundary=new Date(report.split+'T00:00:00Z');
    boundary.setUTCDate(boundary.getUTCDate()-1);
    const last=boundary.toISOString().slice(0,10);
    const short=d=>new Intl.DateTimeFormat('en-GB',{day:'numeric',month:'short',year:'numeric',timeZone:'UTC'}).format(new Date(d+'T00:00:00Z'));
    return [last<report.start?'Before '+short(report.split):short(report.start)+' to '+short(last),short(report.split)+' to '+short(report.end)];
}
function buyerReason(f,c){
    const products=new Map(), combinations=new Map();
    for(const r of c.receipts){
        const names=new Set(), labels=new Set();
        for(const part of r.parts){
            for(const n of part.needs){
                if(!r.abstained)labels.add(n.label);
                if(f.kind==='Mixed basket'||(f.kind==='Shopping mission'&&f.label===n.label))
                    n.support.forEach(name=>names.add(name));
            }
            if(c.counts)part.products.forEach((name,k)=>{if(part.categories[k]===f.label)names.add(name)});
        }
        for(const name of names)products.set(name,(products.get(name)||0)+1);
        const combination=[...labels].sort().join(' + ');
        if(combination)combinations.set(combination,(combinations.get(combination)||0)+1);
    }
    const ranked=m=>[...m].sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0]));
    let reason='';
    if(c.counts){
        const [a,n,b,m]=c.counts;
        reason='<div class="comparison">'+[[a,n],[b,m]].map(([hits,trips],k)=>
            '<div><small>'+ranges()[k]+'</small><strong>'+(trips?Math.round(100*hits/trips)+'%':'No trips')+'</strong><span>'+hits+' of '+trips+' trips included '+esc(f.label)+'</span></div>').join('<span aria-hidden="true">&rarr;</span>')+'</div>';
    }else if(f.kind==='Mixed basket'){
        const top=ranked(combinations)[0];
        if(top)reason='<p>The most frequent combination here was <strong>'+esc(top[0])+'</strong>, seen on '+top[1]+' of '+c.receipts.length+' matching trips.</p>';
    }else{
        reason='<p>These products serve '+esc(f.label.toLowerCase())+'. Their presence on '+c.receipts.length+' matching trips is why the engine suggests this mission.</p>';
    }
    return '<section><h2>Why this finding appears</h2>'+reason+'<h3>Products behind this finding</h3><ul>'+ranked(products).slice(0,5).map(([name,n])=>'<li>'+esc(name)+' · '+n+' of '+c.receipts.length+' matching trips</li>').join('')+'</ul></section>';
}
function explanation(f){
    const [early,late]=ranges();
    const category=f.label.toLowerCase();
    switch(f.kind){
        case 'Established routine':return 'These buyers chose '+category+' on at least half their trips in '+early+' and again in '+late+'.';
        case 'Occasional purchase':return 'These buyers chose '+category+' during '+early+' and again during '+late+', with no large change in its share of trips.';
        case 'Limited history':return 'Comparing '+early+' with '+late+' requires at least two recorded trips in each date range.';
        case 'Newly observed':return 'These buyers first recorded a purchase of '+category+' during '+late+'.';
        case 'More frequent':case 'Less frequent':return 'Compare how often these buyers chose '+category+' during '+early+' and '+late+'.';
        default:return descriptions[f.kind];
    }
}
function cohort(f){
    const e=report.category_evidence[f.label];
    if(!e||['Mixed basket','Shopping mission'].includes(f.kind)) return '';
    return '<details class="panel"><summary>Wider category evidence</summary><p>Across all '+e.buyers+' buyers with enough trips before and after the split date, the average change was '+e.change+' percentage points. A percentage point is the difference between two percentages.</p><p>95% buyer-bootstrap interval: '+e.low+' to '+e.high+' points. Directional sign test, corrected across categories: q = '+e.q+'. This describes the wider group, not just the buyers selected for this finding.</p></details>';
}
function mainFinding(x){
    if(['Shopping mission','Mixed basket'].includes(x.kind))return true;
    if(x.kind==='Established routine')return x.buyers>=2;
    const changes=['Newly observed','More frequent','Less frequent','No recent purchase'];
    const e=report.category_evidence[x.label];
    if(!changes.includes(x.kind)||x.buyers<2||!e||!e.supported)return false;
    return ['Newly observed','More frequent'].includes(x.kind)?e.low>0:e.high<0;
}
let lastListing='';
function findings(s, exploratory){
    const listing=exploratory?'exploratory':'findings';
    if(lastListing!==listing){query='';filter='All findings';lastListing=listing}
    const entries=report.findings.map((x,i)=>({...x,i})).filter(x=>mainFinding(x)!==exploratory);
    const heading=exploratory?intro('WORKSPACE / EXPLORATORY','Exploratory observations','These purchase patterns may fall outside a known shopping need or have too little evidence for a wider conclusion. Treat them as hypotheses for review. Each row names the category and counts the buyers and receipts behind it. Open a row to see whether the actual purchases support your interpretation.'):
        intro('WORKSPACE / FINDINGS',s.sample?'Example findings':'Synthetic receipt findings',report.total.toLocaleString()+' receipts · '+report.buyers+' identified buyers · '+esc(report.start)+' to '+esc(report.end));
    view.innerHTML=heading+'<div class="bar"><label>Finding type <select id="filter">'+['All findings',...new Set(entries.map(f=>f.kind))].map(k=>'<option>'+esc(k)+'</option>').join('')+'</select></label><label>Search <input id="search" placeholder="Category or mission"></label></div><div id="cards"></div><details class="panel"><summary>How we compare shopping trips</summary><p>We compare '+ranges().join(' with ')+'. Each buyer needs at least two trips in each date range for a frequency comparison. We use 25 percentage points as the cutoff for a frequency change. For example, buying on 2 of 4 trips and then 3 of 4 moves from 50% to 75%.</p><p>'+report.variants+' receipt spellings were grouped into '+report.families+' product families.</p></details>';const f=document.querySelector('#filter'),q=document.querySelector('#search');f.value=filter;q.value=query;
    if(exploratory&&!entries.length){
        view.innerHTML=heading+'<p>This workbook has no additional purchase patterns to review. You can explore its main findings instead.</p>'+btn('findings','View findings');
        return;
    }

    function draw(){
        const sections=[
            ['Shopping missions',['Shopping mission']],
            ['Established routines',['Established routine']],
            ['Mixed baskets',['Mixed basket']],
            ['Changes in purchasing',['Newly observed','More frequent','Less frequent','No recent purchase']],
            ['Other observations',['Occasional purchase','Limited history']]
        ];
        const html=sections.map(([title,kinds])=>{
            const rows=entries.filter(x=>kinds.includes(x.kind) && (filter==='All findings'||filter===x.kind) && x.label.toLowerCase().includes(query.toLowerCase()));
            if(!rows.length)return '';
            return '<section class="finding-section"><h2>'+title+'</h2>'+rows.map(x=>'<article><h3><a href="#evidence/'+x.i+'">'+esc(x.label)+'</a></h3><p>'+esc(x.kind)+' · '+esc(x.kind==='Shopping mission'?missionText(x):x.inference||explanation(x))+'</p><small>'+x.buyers+' identified buyers · '+x.baskets+' receipts</small></article>').join('')+'</section>';
        }).join('');
        view.querySelector('#cards').innerHTML=html||'<p>No matches. Try another search or type.</p>';
    }
    f.onchange=()=>{filter=f.value;draw()};q.oninput=()=>{query=q.value;draw()};
    draw();
}

async function evidence(i,j,version){if(i===undefined||!report.findings[i]){view.innerHTML=intro('WORKSPACE / CUSTOMER EVIDENCE','Choose a finding','Each finding has its own group of buyers and supporting receipts.')+btn('findings','Browse findings →');return}const f=report.findings[i],buyers=await api('evidence?finding='+i),c=await api('evidence?finding='+i+'&buyer='+j);if(epoch!==version)return;view.innerHTML=(mainFinding(f)?'<a class="back" href="#findings">← All findings</a>':'<a class="back" href="#exploratory">← Exploratory observations</a>')+intro('CUSTOMER EVIDENCE / '+esc(f.kind.toUpperCase()),esc(f.label),esc(explanation(f)))+'<div class="bar"><label>Buyer <select id="buyer">'+buyers.map((b,k)=>'<option value="'+k+'">'+esc(b??'Unidentified receipts')+'</option>').join('')+'</select></label></div>'+buyerReason(f,c)+findingBrands(f,c)+cohort(f)+'<p>Open a trip to see which products support this finding. Highlighted products contributed to the selected mission or category.</p><h2 class="section">Supporting receipts</h2>'+c.receipts.sort((a,b)=>b.date.localeCompare(a.date)).map(r=>'<details class="panel"><summary>'+esc(r.date)+' · Receipt '+esc(r.id)+'</summary>'+(r.abstained?'<p>Mission withheld: the available evidence is too weak or incomplete.</p>':'')+r.parts.map(p=>'<section class="receipt"><h3>'+esc(!r.abstained&&p.needs.length?p.needs.map(n=>n.label).join(' / '):'Products without a clear mission')+'</h3><small>'+esc((p.basis||'').replace('across both periods','in each half of the receipt history').replace('in only one period','in only one half of the receipt history'))+'</small><p>'+p.products.map((name,k)=>{
    const match=p.categories?.[k]===f.label||p.needs.some(n=>(f.kind==='Mixed basket'||n.label===f.label)&&n.support.includes(name));
    return (match?'<mark>'+esc(name)+'</mark>':esc(name))+(p.prices?.[k]!=null?' (unit price '+esc(p.prices[k])+')':'')+Object.entries(p.attributes?.[k]||{}).map(([key,values])=>' · '+esc(key)+': '+values.map(esc).join(', ')).join('');
}).join(' · ')+'</p>'+(p.ambiguous.length?'<p>Could fit another group: '+p.ambiguous.map(esc).join(', ')+'</p>':'')+'</section>').join('')+'<details><summary>Scoring evidence</summary><p>Receipt completeness: '+pct(r.quality)+' · Model confidence (rule based): '+pct(r.confidence)+' · Gap between the strongest two candidate scores: '+pct(r.margin)+'.</p>'+r.parts.flatMap(p=>p.needs.map(n=>'<p>'+esc(n.label)+' · independent score '+pct(n.score)+' · supported by '+n.support.map(esc).join(', ')+'</p>')).join('')+'</details></details>').join('');const b=document.querySelector('#buyer');b.value=j;b.onchange=()=>location.hash='evidence/'+i+'/'+b.value}
const pct=v=>Math.round(v*100)+'/100';
async function route(){const version=++epoch;try{const [page='start',i,j='0']=location.hash.slice(1).split('/'),s=await api('state');if(version!==epoch)return;token=s.token;const name=page||'start';document.querySelectorAll('nav a').forEach(a=>{a.removeAttribute('aria-current');if(a.hash==='#'+name||(a.hash==='#outlook'&&name==='brands'))a.setAttribute('aria-current','page')});if(name==='start')start();else if(name==='import')importPage(s);else if(!s.available&&name==='exploratory')view.innerHTML=intro('WORKSPACE','Exploratory observations','Import a workbook to look for purchase patterns worth reviewing.')+btn('import','Import receipts');else if(!s.available)empty();else{report=report&&report.version===s.version?report:await api('findings');if(version!==epoch)return;if(name==='brands')brandsPage(location.hash.slice(1).split('/'));else if(name==='brand-history')brandHistory(location.hash.slice(1).split('/'));else if(name==='outlook')outlook();else if(name==='goals')await goals(version);else if(name==='evidence')await evidence(i,j,version);else findings(s,name==='exploratory')}window.scrollTo(0,0);view.focus()}catch(e){feedback(e.message)}}
window.addEventListener('hashchange',route);route();
