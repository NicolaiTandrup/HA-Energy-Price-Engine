// Browser regression coverage complementary to the real native HA acceptance run.
// Fixtures come from test_dashboard.py's actual HA/SQLite/source snapshots.
import {test, before, after} from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFile} from 'node:fs/promises';
import {resolve} from 'node:path';
const {chromium} = await import(process.env.PE_PLAYWRIGHT_MODULE || 'playwright');
const dataRoot = process.env.PE_FRONTEND_FIXTURES;
assert.ok(dataRoot, 'Set PE_FRONTEND_FIXTURES using real producer fixture exports');
let server, browser, url;
const HTML = `<!doctype html><html><head><meta charset="utf-8"><title>PE card regression</title><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{margin:0;background:#f7f8fa;font-family:Arial}energy-price-engine-card{display:block;max-width:1440px;margin:auto}ha-card{display:block;background:#fff}</style><script type="module" src="/card.js"></script></head><body><energy-price-engine-card></energy-price-engine-card><script>window.PE_XSS=false;window.wsCalls=0;window.load=async(name,language='en',number_format='language')=>{window.fixture=await (await fetch('/data/'+name+'.json')).json();const c=document.querySelector('energy-price-engine-card');await customElements.whenDefined('energy-price-engine-card');c.setConfig({});c.hass={locale:{language,number_format},states:{'sensor.qa_current':{last_updated:String(Date.now())}},connection:{},callWS:async msg=>{window.wsCalls++;if(msg.type==='ha_energy_price_engine/sites')return [{site_id:window.fixture.site.id,name:window.fixture.site.name,entity_id:'sensor.qa_current'}];if(msg.type!=='ha_energy_price_engine/price_schedule'||msg.site_id!==window.fixture.site.id)throw Error('Unexpected command');return structuredClone(window.fixture)}};};</script></body></html>`;
before(async()=>{
 server=createServer(async(req,res)=>{
  try {
   if(req.url==='/'){res.setHeader('Content-Type','text/html');res.end(HTML);}
   else if(req.url==='/card.js'){res.setHeader('Content-Type','text/javascript');res.end(await readFile(resolve('custom_components/ha_energy_price_engine/www/energy-price-engine-card.js')));}
   else if(/^\/data\/[a-z-]+\.json$/.test(req.url)){res.setHeader('Content-Type','application/json');res.end(await readFile(resolve(dataRoot,req.url.split('/').at(-1))));}
   else if(req.url==='/favicon.ico'){res.statusCode=204;res.end();}
   else {res.statusCode=404;res.end();}
  } catch(err){res.statusCode=500;res.end(String(err));}
 });
 await new Promise(r=>server.listen(0,'127.0.0.1',r));url=`http://127.0.0.1:${server.address().port}`;
 browser=await chromium.launch({headless:true,...(process.env.PE_CHROMIUM ? {executablePath:process.env.PE_CHROMIUM}:{}),args:['--no-sandbox']});
});
after(async()=>{await browser?.close();await new Promise(r=>server.close(r));});
async function open(name,width=1440,language='en',format='language'){
 const page=await browser.newPage({viewport:{width,height:1000},locale:'en-GB'});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',e=>{if(['error','warning'].includes(e.type()))errors.push(e.text());});
 await page.goto(url);await page.evaluate(([n,l,f])=>window.load(n,l,f),[name,language,format]);
 const card=page.locator('energy-price-engine-card');await card.locator('.chart').first().waitFor();
 return {page,card,errors};
}
for(const [name,count] of [['normal',196],['fall',196],['spring',188]]) for(const width of [1440,390]){
 test(`${name} ${width}px: two series, every quarter and local offsets`,async()=>{
  const {page,card,errors}=await open(name,width);
  assert.equal(await page.title(),'PE card regression');
  assert.equal(await card.locator('[data-chart]').count(),2);
  assert.equal(await card.locator('[data-chart="spot"] rect.bar').count(),count);
  assert.equal(await card.locator('[data-chart="final"] rect.bar').count(),count);
  assert.equal(await card.locator('[data-table="schedule"] tbody tr').count(),count);
  assert.equal(await card.locator('select option').count(),count);
  assert.equal(await card.locator('[data-table="tariffs"] tbody tr').count(),4);
  assert.equal(await card.locator('.now').count(),2);
  assert.equal(await card.locator('.boundary').count(),2);
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth),width);
  if(name==='fall'){
   const options=await card.locator('select').textContent();
   assert.ok(options.includes('2026-10-25T02:00+02:00'));
   assert.ok(options.includes('2026-10-25T02:00+01:00'));
  }
  const option=await card.locator('select option').last().getAttribute('value');
  await card.locator('select').selectOption(option);
  assert.ok((await card.locator('.inspector').textContent()).includes(option));
  await card.locator('[data-chart="spot"] rect.bar').first().focus();await page.keyboard.press('Enter');
  assert.ok((await card.locator('.inspector').textContent()).includes((await card.locator('select option').first().getAttribute('value'))));
  await card.locator('details').last().locator('summary').click();
  assert.equal(await card.locator('details').last().getAttribute('open'),'');
  await card.locator('[data-refresh]').click();
  assert.equal(await card.locator('details').last().getAttribute('open'),'');
  assert.deepEqual(errors,[]);await page.close();
 });
}
for(const [name,raw,final] of [['missing',196,0],['unpublished',96,96],['gap',196,195]]){
 test(`${name}: visible reasons, unavailable final gaps and independent raw`,async()=>{
  const {page,card,errors}=await open(name,390);
  assert.equal(await card.locator('[data-chart="spot"] rect.bar').count(),raw);
  assert.equal(await card.locator('[data-chart="final"] rect.bar').count(),final);
  assert.ok((await card.locator('ha-card').textContent()).includes('Incomplete') || (await card.locator('ha-card').textContent()).includes('Error') || (await card.locator('ha-card').textContent()).includes('Stale'));
  assert.ok(await card.locator('.notice').count());
  assert.deepEqual(errors,[]);await page.close();
 });
}
test('real source revision changes graph/table/inspector without reloading',async()=>{
 const {page,card,errors}=await open('revision-before');
 const old=await card.locator('[data-chart="final"] rect.bar').last().getAttribute('aria-label');
 await page.evaluate(()=>window.load('revision-after'));
 await page.waitForFunction(old=>{const c=document.querySelector('energy-price-engine-card');return c.shadowRoot.querySelector('[data-chart="final"] rect.bar:last-of-type')?.getAttribute('aria-label')!==old;},old);
 assert.notEqual(await card.locator('[data-chart="final"] rect.bar').last().getAttribute('aria-label'),old);
 const value=await card.locator('select option').last().getAttribute('value');await card.locator('select').selectOption(value);
 assert.ok((await card.locator('.inspector').textContent()).includes('Revision 3'));
 assert.deepEqual(errors,[]);await page.close();
});
for(const [language,format,decimal] of [['en','language','.'],['en-GB','language','.'],['da','language',','],['en','decimal_comma',','],['da','system','.']]){
 test(`${language}/${format}: two decimal ore, negative/zero and escaped sources`,async()=>{
  const {page,card,errors}=await open('varied',390,language,format);
  assert.equal(await card.locator('img').count(),0);assert.equal(await page.evaluate(()=>window.PE_XSS),false);
  assert.ok((await card.locator('.inspector').textContent()).includes('<img src=x'));
  const cells=await card.locator('[data-table="schedule"] td.numeric').allTextContents();
  const pattern=new RegExp(`^-?\\d+\\${decimal}\\d{2}$`);
  assert.ok(cells.length>=192*8 && cells.every(v=>v==='—'||pattern.test(v)));
  assert.ok(cells.some(v=>v.startsWith('-')));assert.ok(cells.includes('0'+decimal+'00'));
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth),390);
  assert.deepEqual(errors,[]);await page.close();
 });
}
for (const language of ['en', 'da']) {
 test(`activation boundary ${language}: explained unknown becomes Ready without inventing history`, async()=>{
  const {page,card,errors}=await open('activation',390,language);
  const text=await card.locator('.activation').innerText();
  assert.ok(/14[:.]15/.test(text) && text.includes(language==='da'?'Næste kvarter er Klar':'next quarter is Ready'));
  assert.ok((await card.locator('.statistics').innerText()).includes(language==='da'?'resten af dagen':'Remaining-day'));
  assert.ok((await card.locator('.health').innerText()).includes(language==='da'?'Ufuldstændig':'Incomplete'));
  await page.evaluate(language=>window.load('activated',language),language);
  await page.waitForFunction(()=>!document.querySelector('energy-price-engine-card').shadowRoot.querySelector('.activation'));
  assert.ok((await card.locator('.statistics').innerText()).includes(language==='da'?'resten af dagen':'Remaining-day'));
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth),390);
  assert.deepEqual(errors,[]);await page.close();
 });
}
