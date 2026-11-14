/* Real browser checks for the custom web workspace. Run with Playwright on NODE_PATH. */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
(async () => {
  const browser = await chromium.launch({channel:'msedge',headless:true});
  const page = await browser.newPage({viewport:{width:1440,height:1000}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const out=path.resolve('data/web-preview');fs.mkdirSync(out,{recursive:true});
  await page.goto('http://127.0.0.1:8502');
  await page.getByRole('heading',{name:/What are your/}).waitFor();
  await page.screenshot({path:path.join(out,'start-desktop.png'),fullPage:true});
  await page.getByRole('button',{name:'Explore sample data',exact:true}).click();
  await Promise.race([
    page.getByRole('heading',{name:'What deserves your attention?'}).waitFor({timeout:300000}),
    page.locator('.error-box').waitFor({timeout:300000}).then(async()=>{throw Error(await page.locator('.error-box').innerText())})
  ]);
  await page.screenshot({path:path.join(out,'findings-desktop.png'),fullPage:true});
  await page.getByRole('button',{name:'Understand this finding'}).first().click();
  await page.getByRole('dialog').waitFor();
  await page.screenshot({path:path.join(out,'finding-detail.png'),fullPage:true});
  await page.getByText('See the statistical evidence',{exact:true}).click();
  await page.getByRole('button',{name:'Close details'}).click();
  await page.getByRole('link',{name:'04 Customers'}).click();
  await page.getByRole('heading',{name:'Follow the customer story.'}).waitFor();
  await page.locator('button.customer-id').first().click();
  await page.getByRole('heading',{name:'Observed routines'}).waitFor();
  await page.screenshot({path:path.join(out,'customer-detail.png'),fullPage:true});
  await page.getByRole('button',{name:/View receipt/}).first().click();
  await page.getByText('OBSERVED PURCHASES',{exact:true}).waitFor();
  await page.getByRole('button',{name:'Close details'}).click();
  await page.getByRole('link',{name:'02 Receipt data'}).click();
  await page.locator('#file-input').setInputFiles(path.resolve('data/raw/DH_Synthtic_Receipt_Database.xlsx'));
  await page.getByText('Format recognised',{exact:true}).waitFor({timeout:120000});
  await page.screenshot({path:path.join(out,'import-preview.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  await page.getByRole('link',{name:'01 Start here'}).click();
  await page.screenshot({path:path.join(out,'start-mobile.png'),fullPage:true});
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);
  if(overflow)errors.push('Mobile horizontal overflow');
  console.log(JSON.stringify({errors,preview:out}));
  await browser.close();if(errors.length)process.exit(1);
})().catch(e=>{console.error(e);process.exit(1)});
