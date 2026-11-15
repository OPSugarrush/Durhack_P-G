const {chromium}=require('playwright');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try{
  const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto((process.env.NEEDSTATE_URL||'http://127.0.0.1:8770')+'/#import');
  await page.getByRole('button',{name:'Generate new ID',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('#customer-id').value.startsWith('C-'));
  console.log('Selected photo upload');
  await page.locator('#upload-file').setInputFiles('receipt_ingestion/examples/demo_receipt.png');
  await page.getByRole('button',{name:'Read receipt',exact:true}).click();
  console.log('Started extraction');
  await page.locator('.receipt-content').waitFor({timeout:120000});
  console.log('Extraction ready');
  await page.getByText('Correct extraction',{exact:true}).click();
  await page.locator('[data-meta="date"]').fill('2026-04-01');
  await page.locator('#save-review').click();
  await page.waitForFunction(()=>document.querySelector('.receipt-content').textContent.includes('2026-04-01'));
  await page.setViewportSize({width:390,height:844});
  if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1))throw Error('Receipt review overflows on mobile');
  await page.setViewportSize({width:1280,height:900});
  await page.screenshot({path:'artifacts/import-review.png',fullPage:true});
  await page.getByRole('button',{name:'Focus on this upload',exact:true}).click();
  await page.getByRole('heading',{name:'Your purchases'}).waitFor({timeout:120000});
  await page.getByRole('link',{name:'Import more receipts',exact:true}).click();
  await page.getByRole('button',{name:'Add to my data',exact:true}).click();
  await page.getByText('All data in this session',{exact:true}).waitFor({timeout:120000});
  await page.getByRole('link',{name:'Import more receipts',exact:true}).click();
  await page.getByRole('button',{name:'Focus on this upload',exact:true}).click();
  await page.getByRole('button',{name:'Back to all data',exact:true}).click();
  await page.getByText('All data in this session',{exact:true}).waitFor();
  await page.screenshot({path:'artifacts/import-summary.png',fullPage:true});
  if(errors.length)throw Error(errors.join('\n'));
  console.log('PASS actual photo OCR, saved review, mobile layout, focus, append and return to collection');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
