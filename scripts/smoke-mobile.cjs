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
 const server=spawn(process.execPath,[require.resolve('vite/bin/vite.js'),'preview','--host','127.0.0.1','--port','4173','--strictPort'],{stdio:'inherit'});
 let browser;
 try{
  await waitForServer();
  browser=await chromium.launch({headless:true,args:['--no-sandbox']});
  for(const viewport of [{width:360,height:800},{width:390,height:844},{width:768,height:1024}]){
   const page=await browser.newPage({viewport,deviceScaleFactor:1,locale:'pt-BR',reducedMotion:'reduce'});
   const errors=[];
   page.on('pageerror',err=>errors.push(err.message));
   await page.goto(origin,{waitUntil:'domcontentloaded',timeout:20000});
   await page.locator('#nav-mobile .sidebar-link.active').waitFor({timeout:20000});
   await check((await page.locator('#nav-mobile .sidebar-link.active').getAttribute('data-page'))==='municipal','Página inicial não é municipal');
   const activePages=[];
   for(const route of routes){
    const selector=page.locator('#nav-mobile [data-page="'+route+'"]');
    await selector.click({timeout:20000});
    const active=page.locator('#nav-mobile .sidebar-link.active');
    await active.waitFor({timeout:10000});
    await check((await active.getAttribute('data-page'))===route,'Aba ativa incorreta em '+route);
    await page.waitForTimeout(100);
    const rect=await page.evaluate(()=>{
      const nav=document.querySelector('#nav-mobile');
      const tab=nav?.querySelector('.sidebar-link.active');
      return {tabX:tab?.getBoundingClientRect().left,navX:nav?.getBoundingClientRect().left,
       docW:document.documentElement.scrollWidth,screenW:window.innerWidth}
    });
    await check(rect.tabX!==undefined&&Math.abs(rect.tabX-rect.navX-12)<35,
      'Aba ativa não alinhada à esquerda em '+route+': '+JSON.stringify(rect));
    await check(rect.docW<=rect.screenW+4,'Overflow horizontal em '+route+': '+JSON.stringify(rect));
    activePages.push(route);
    if(viewport.width===390&&['municipal','overview','health','vital','sus','aps-history','screening','finance','production','sources'].includes(route)){
      await page.screenshot({path:path.join(snapDir,route+'-390px.png'),fullPage:true,animations:'disabled'});
    }
   }
   await page.locator('#nav-mobile [data-page="sources"]').click();
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
