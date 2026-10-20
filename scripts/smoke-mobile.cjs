/* Navegação mobile com navegador real (Chromium headless). Não usa serviços privados. */
const { chromium }=require('playwright');
const {spawn}=require('node:child_process');
const {mkdirSync}=require('node:fs');
const {setTimeout:delay}=require('node:timers/promises');
const path=require('node:path');

const origin='http://127.0.0.1:4173';
const snapDir=path.resolve('artifacts/mobile-ux');
const routes=[
  'municipal','overview','map','facilities','health','vital','sus',
  'aps-history','screening','finance','production','sources'
];
async function check(condition,detail){if(!condition)throw new Error(detail)}
async function waitForServer(){
 for(let i=0;i<45;i++){
  try{const result=await fetch(origin);if(result.ok)return}catch{}
  await delay(1000);
 }
 throw new Error('Vite preview não respondeu em 45 segundos');
}
async function main(){
 mkdirSync(snapDir,{recursive:true});
 const server=spawn(process.execPath,[path.resolve('node_modules/vite/bin/vite.js'),'preview','--host','127.0.0.1','--port','4173','--strictPort'],{stdio:'inherit'});
 let browser;
 try{
  await waitForServer();
  browser=await chromium.launch({headless:true,args:['--no-sandbox']});
  for(const viewport of [{width:360,height:800},{width:390,height:844},{width:768,height:1024}]){
   const page=await browser.newPage({viewport,deviceScaleFactor:1,locale:'pt-BR',reducedMotion:'reduce'});
   const errors=[];
   page.on('pageerror',err=>errors.push(err.message));
   await page.goto(origin,{waitUntil:'domcontentloaded',timeout:20000});
   await page.locator('[data-open-nav]').waitFor({timeout:20000});
   await page.locator('[data-open-nav]').click();
   await check((await page.locator('#mobile-drawer .sidebar-link.active').getAttribute('data-page'))==='municipal','Página inicial não é municipal');
   await page.locator('#close-nav').click();
   const activePages=[];
   for(const route of routes){
    await page.locator('[data-open-nav]').click();
    const selector=page.locator('#mobile-drawer [data-page="'+route+'"]');
    const group=selector.locator('xpath=ancestor::section[contains(@class,"nav-group")]');
    if(await group.count()){
      const toggle=group.locator('[data-nav-group]');
      if(await toggle.getAttribute('aria-expanded')==='false')await toggle.click();
    }
    await selector.click({timeout:20000});
    await check((await page.locator('#mobile-drawer .sidebar-link.active').getAttribute('data-page'))===route,'Página ativa incorreta em '+route);
    await check(await page.locator('#mobile-drawer').isHidden(),'Menu lateral não fechou em '+route);
    await page.locator('[data-open-nav]').click();
    const active=page.locator('#mobile-drawer .sidebar-link.active');
    const rect=await active.boundingBox();
    const panel=await page.locator('.drawer-panel').boundingBox();
    await check(!!rect&&!!panel&&rect.x>=panel.x&&rect.x<panel.x+50,
      'Página ativa não está alinhada à esquerda em '+route+': '+JSON.stringify({rect,panel}));
    await page.locator('#close-nav').click();
    const width=await page.evaluate(()=>document.documentElement.scrollWidth);
    await check(width<=viewport.width+4,'Overflow horizontal em '+route+': '+width);
    activePages.push(route);
    if(viewport.width===390&&['municipal','overview','health','vital','sus','aps-history','screening','finance','production','sources'].includes(route)){
      await page.screenshot({path:path.join(snapDir,route+'-390px.png'),fullPage:true,animations:'disabled'});
    }
   }
   await page.locator('[data-open-nav]').click();await page.locator('#mobile-drawer [data-page="sources"]').click();
   await page.locator('#source-groups details').first().waitFor({timeout:20000});
   await check((await page.locator('#source-groups details').count())>=3,'Catálogo incompleto');
   await check(!errors.some(e=>/TypeError|ReferenceError|SyntaxError/.test(e)),
      'Erros JavaScript em '+viewport.width+'px: '+errors.join('; '));
   console.log('MOBILE_SMOKE_OK',viewport.width,activePages.length,'páginas, sem overflow de documento');
   await page.close();
  }
 }finally{
  if(browser)await browser.close();
  server.kill('SIGTERM');
 }
}
main().catch(error=>{console.error('MOBILE_SMOKE_FAILED',error);process.exitCode=1});
