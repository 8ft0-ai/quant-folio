const puppeteer = require("puppeteer");
(async()=>{
 const browser=await puppeteer.launch({headless:true,executablePath:"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"});
 for(const width of [1440,640,390,320]){
  const p=await browser.newPage();
  await p.setViewport({width,height:900});
  const local = require("node:url").pathToFileURL(require("node:path").resolve(__dirname,"../site/index.html")).href;
  await p.goto(local);
  const size=await p.evaluate(()=>document.documentElement.scrollWidth);
  if(size>width)throw Error("reflow "+width+" "+size);
  await p.focus('[data-filter="risk"]');
  await p.keyboard.press("Enter");
  const n=await p.$$eval(".paper-row:not([hidden])",a=>a.length);
  if(n!==1)throw Error("keyboard filter "+width);
  const progress=await p.$eval("#reading-progress",e=>e.getAttribute("aria-label"));
  if(progress!=="Reading progress")throw Error("progress label");
  if(width<=640){
   const show=await p.$eval(".nav-more",e=>!e.hidden);
   if(!show)throw Error("navigation cue missing "+width);
   await p.focus(".nav-more");await p.keyboard.press("Enter");
   const moved=await p.$eval(".rail-nav",e=>e.scrollLeft);
   if(moved<1)throw Error("navigation cue inactive "+width);
  }
  const ax=await p.createCDPSession();
  const tree=(await ax.send("Accessibility.getFullAXTree")).nodes;
  if(!tree.some(n=>n.role?.value==="progressbar" && n.name?.value==="Reading progress"))throw Error("missing accessible progress");
  console.log("PASS",width);
  await p.close();
 }
 await browser.close();
})().catch(e=>{console.error(e);process.exitCode=1});
