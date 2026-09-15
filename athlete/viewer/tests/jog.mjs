/** Exercise the actual preview and measure the exported joints between keys. */
import {createRequire} from 'node:module'
import fs from 'node:fs'
import path from 'node:path'
import assert from 'node:assert/strict'
const require=createRequire('F:/Repositories/braven-tactics-netball-athlete/package.json')
const browser=await require('puppeteer-core').launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,defaultViewport:{width:1440,height:1000}})
const page=await browser.newPage(),checks=[],errors=[],out=path.resolve('verification/jog');fs.mkdirSync(out,{recursive:true})
page.on('pageerror',e=>errors.push(String(e)))
const check=(name,ok,detail)=>{checks.push({name,passed:!!ok,detail});assert(ok,`${name}: ${JSON.stringify(detail)}`)}
try{
 await page.goto('http://127.0.0.1:5397/',{waitUntil:'networkidle0'});await page.waitForFunction(()=>window.athleteStudio)
 await page.select('#clip','Jog')
 check('Selecting Jog starts playback',await page.evaluate(()=>window.athleteStudio.state.playing&&window.athleteStudio.state.clip==='Jog'))
 await page.click('#side')
 const metrics=await page.evaluate(()=>{
  const a=window.athleteStudio;a.pause();const rows=[],at=n=>a.bones.get(n).getWorldPosition(a.model.position.clone())
  for(let i=0;i<248;i++){a.seek(a.duration()*i/248);for(const s of ['l','r']){const ankle=at('foot_'+s),shin=at('calf_'+s).sub(ankle),toe=at('ball_'+s).sub(ankle);rows.push(shin.angleTo(toe)*180/Math.PI)}}
  return{min:Math.min(...rows),max:Math.max(...rows),samples:rows.length,seconds:a.duration(),revision:a.assetRevision,hash:a.assetHash}
 })
 check('Both ankles stay in the reviewed 55–140 degree envelope',metrics.min>55&&metrics.max<140,metrics)
 check('Jog cadence is unchanged',Math.abs(metrics.seconds-62/60)<1e-6,metrics.seconds)
 for(const kit of ['skirt','shorts']){
  await page.click('[data-tab="kit"]');await page.click(`[data-kit="${kit}"]`);await page.click('[data-tab="animate"]')
  for(const view of ['side','front']){await page.click('#'+view);for(const t of [.13,.26,.39,.65,.78]){
   await page.evaluate(t=>{const a=window.athleteStudio;a.seek(t);a.renderer.render(a.scene,a.camera)},t)
   await page.screenshot({path:`${out}/${kit}-${view}-${t}.png`})
  }}
  check(`${kit} remains selected through scrubbing`,await page.evaluate(kit=>window.athleteStudio.state.kit===kit,kit))
 }
 await page.click('#play');const before=await page.evaluate(()=>window.athleteStudio.state.time)
 await new Promise(r=>setTimeout(r,2100));const after=await page.evaluate(()=>({time:window.athleteStudio.state.time,playing:window.athleteStudio.state.playing}))
 check('Jog loops through real playback',after.playing&&Math.abs(after.time-before)>.005,after)
 check('No application exceptions',!errors.length,errors)
 const build=await page.evaluate(async()=>await(await fetch('/studio-build.json')).json())
 fs.writeFileSync(out+'/browser.json',JSON.stringify({checks,metrics,build,errors},null,2));console.log(JSON.stringify({checks:checks.length,metrics,build:build.buildId}))
}finally{await browser.close()}
