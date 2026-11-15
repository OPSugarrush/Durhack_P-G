const {chromium}=require('playwright');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1280,height:900}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(process.env.NEEDSTATE_URL||'http://127.0.0.1:8774');
  if(await page.getByRole('button',{name:'Explore example',exact:true}).count())throw Error('Example entry still visible');
  await page.getByRole('link',{name:'Import receipts',exact:true}).click();
  if(await page.locator('#upload-review table').count())throw Error('Default receipt should be empty');
  await page.getByRole('button',{name:'Generate new ID',exact:true}).click();
  await page.waitForFunction(()=>/^C-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(document.querySelector('#customer-id').value));
  const id=await page.locator('#customer-id').inputValue();
  const paths=process.argv.slice(2);
  for(let i=0;i<paths.length;i++){
   await page.locator('#customer-id').fill(id);
   await page.locator('#upload-file').setInputFiles(paths[i]);
   await page.getByRole('button',{name:'Read receipt',exact:true}).click();
   await page.waitForFunction(n=>document.querySelectorAll('.result-items tbody tr').length===n,i===0?3:7,{timeout:120000});
   if(await page.locator('.corrections').evaluate(e=>e.open))throw Error('Correction form should be collapsed');
   if((await page.locator('.customer-code').textContent())!==id)throw Error('Customer identity changed');
   const expected=i===0?'2025-11-25':'2026-11-14';
   if(!(await page.locator('.receipt-content').textContent()).includes(expected))throw Error('Date not automatically extracted');
   await page.locator('.receipt-image img').evaluate(img=>img.decode());
   await page.screenshot({path:'artifacts/receipt-layout-'+i+'.png',fullPage:true});
   await page.setViewportSize({width:390,height:844});
   if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1))throw Error('Mobile overflow');
   await page.setViewportSize({width:1280,height:900});
   await page.getByRole('button',{name:'Focus on this upload',exact:true}).click();
   await page.getByRole('heading',{name:'Your purchases',exact:true}).waitFor({timeout:120000});
   await page.getByRole('link',{name:'Import more receipts',exact:true}).click();
  }
  if(errors.length)throw Error(errors.join('\n'));
  console.log('PASS supplied receipt layouts, automatic dates, UUID customer reuse, collapsed corrections, focus and mobile width');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
