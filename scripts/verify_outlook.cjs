// Run against the local review server with Playwright available on NODE_PATH.
const {chromium}=require('playwright');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try {
  const page=await browser.newPage({viewport:{width:1280,height:900}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(process.env.NEEDSTATE_URL||'http://127.0.0.1:8767');
  const state=await (await page.request.get((process.env.NEEDSTATE_URL||'http://127.0.0.1:8767')+'/api/state')).json();
  await page.request.post((process.env.NEEDSTATE_URL||'http://127.0.0.1:8767')+'/api/sample',{headers:{'X-Workspace':state.token}});
  await page.waitForFunction(async()=>{const s=await (await fetch('/api/state')).json();return s.phase==='ready';},{timeout:90000});
  await page.goto((process.env.NEEDSTATE_URL||'http://127.0.0.1:8767')+'/#outlook');
  await page.getByRole('heading',{name:'Leading categories',exact:true}).waitFor({timeout:90000});
  if(!await page.locator('#reach-chart svg').count())throw Error('Missing reach chart');
  const download=page.waitForEvent('download');
  await page.getByRole('button',{name:'Download investigation brief',exact:true}).click();
  if((await download).suggestedFilename()!=='category-investigation.txt')throw Error('Missing investigation export');
  await page.getByRole('link',{name:'Brands & companies',exact:true}).click();
  await page.getByRole('heading',{name:'Understand brand choice',exact:true}).waitFor();
  await page.locator('#brand-category').selectOption({index:1});
  await page.getByRole('link',{name:'Category opportunities',exact:true}).click();
  await page.getByRole('heading',{name:'Leading categories',exact:true}).waitFor();
  if(await page.locator('#category-outlook .movement-chart').count())throw Error('Brand charts leaked into category overview');
  await page.getByRole('link',{name:/Shopper profiles/}).click();
  await page.getByRole('heading',{name:'Brand behaviour',exact:true}).waitFor();
  await page.getByRole('link',{name:'View history →',exact:true}).first().click();
  await page.locator('#history-filter').waitFor();
  await page.getByRole('link',{name:/Back to shopper profiles/}).click();
  await page.getByRole('heading',{name:'Brand behaviour',exact:true}).waitFor();
  await page.setViewportSize({width:390,height:844});
  await page.getByRole('link',{name:/Business outlook/}).click();
  await page.getByRole('heading',{name:'Leading categories',exact:true}).waitFor();
  if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Mobile horizontal overflow');
  if(errors.length)throw Error(errors.join('\n'));
  console.log('PASS reach/change charts, profile history navigation, mobile width and browser errors');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
