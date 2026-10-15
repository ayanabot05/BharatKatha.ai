const { chromium } = require('C:/Users/gunak/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{
const browser=await chromium.launch({channel:'msedge',headless:true});
const page=await browser.newPage();
const errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.route('**/api/**',async route=>{const p=new URL(route.request().url()).pathname;
const data=p==='/api/auth/me'?{id:'ui-test',name:'Beta Tester',email:'tester@example.invalid',plan:'free'}:p==='/api/projects/page'?{items:[],total:0,ready:0,page:1,size:12}:p==='/api/coach/reports'?[]:{};
await route.fulfill({json:data});});
for(const width of [320,390,768,1440]){
await page.setViewportSize({width,height:900});
for(const route of ['/','/dashboard','/coach','/settings']){
await page.goto('http://localhost:3003'+route);await page.waitForTimeout(700);
const box=await page.evaluate(()=>({width:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth}));
if(box.scroll>box.width+1)errors.push(`${route} overflows at ${width}: ${box.scroll}`);
if(width===390||width===1440)await page.screenshot({path:`test_reports/phase0-${route.replace('/','')||'landing'}-${width}.png`,fullPage:true});
console.log(route,width,box.scroll);
}}
await browser.close();if(errors.length){console.error(errors);process.exit(1);}console.log('Responsive checks passed');
})().catch(e=>{console.error(e.message);process.exit(1)});
