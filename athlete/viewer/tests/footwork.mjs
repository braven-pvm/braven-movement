import {createRequire} from 'node:module'
import fs from 'node:fs'
import path from 'node:path'
import assert from 'node:assert/strict'
const require=createRequire('F:/Repositories/braven-tactics-netball-athlete/package.json')
const browser=await require('puppeteer-core').launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,defaultViewport:{width:1440,height:1000}})
const page=await browser.newPage(),checks=[],errors=[],out=path.resolve('verification/footwork');fs.mkdirSync(out,{recursive:true})
page.on('pageerror',e=>errors.push(String(e)))
const check=(name,ok,detail)=>{checks.push({name,passed:!!ok,detail});assert(ok,name+': '+JSON.stringify(detail))}
try{
  await page.goto('http://127.0.0.1:5397/',{waitUntil:'networkidle0'});await page.waitForFunction(()=>window.bravenStudio)
  await page.select('#clip','netball_bounce_pass')
  await page.select('#driver','tactics');await page.select('#scenario','receive-pivot')
  check('Moving receive resets the previous wide bounce camera',await page.evaluate(()=>window.athleteStudio.camera.position.length()<5.5))
  check('Selecting moving receive starts playback and shows its actual title',await page.evaluate(()=>window.athleteStudio.state.playing&&document.getElementById('stage-title').textContent==='Moving receive, pivot and pass'))
  const rows=await page.evaluate(()=>{
    const app=window.athleteStudio;app.pause()
    return [.8,1.2,1.4,1.8,2,2.2,2.4,2.6,2.8,2.2].map(time=>{app.seek(time);const rig=app.rig,point=n=>rig.bone[n].getWorldPosition(rig.group.position.clone()).toArray();return{time,left:point('foot_l'),right:point('foot_r'),ball:point('Ball_Control'),feet:rig.group.userData.athleteFootwork,visible:rig.group.getObjectByName('Movement_Ball').visible}})
  })
  check('Preview includes travel, settling, pivot and a real ball',rows.some(r=>r.feet?.mode==='travel')&&rows.some(r=>r.feet?.mode==='settle')&&rows.some(r=>r.feet?.mode==='pivot')&&rows.every(r=>r.visible))
  const pivot=rows.filter(r=>r.time>=2&&r.time<=2.8)
  check('Pivot support foot stays within 4 mm',pivot.every(r=>Math.hypot(...r.right.map((v,i)=>v-pivot[0].right[i]))<.004),pivot)
  check('Reverse scrub restores the exact pose and ball',JSON.stringify(rows.find(r=>r.time===2.2))===JSON.stringify(rows.at(-1)))
  await page.screenshot({path:out+'/pivot.png'})
  for(const height of [1.6,1.95]){
    await page.click('[data-tab="kit"]');await page.$eval('#height',(el,h)=>{el.value=h;el.dispatchEvent(new Event('input',{bubbles:true}))},height)
    check(`Height ${height} keeps the foot solver reachable`,await page.evaluate(()=>{const a=window.athleteStudio;a.seek(2.2);return Math.max(...Object.values(a.rig.group.userData.athleteFootwork.residual))<.004}))
  }
  await page.click('[data-tab="animate"]');await page.click('#save-setup');await page.$eval('#setup-name',el=>el.value='Moving receive review');await page.click('#save-form [type="submit"]')
  await page.reload({waitUntil:'networkidle0'});await page.waitForFunction(()=>window.bravenStudio)
  check('Saved moving-receive setup restores paused after reload',await page.evaluate(()=>{const a=window.athleteStudio;return a.state.scenario==='receive-pivot'&&a.state.driver==='tactics'&&!a.state.playing&&Math.abs(a.state.time-2.2)<.01}))
  await page.select('#scenario','gait');check('Returning to gait restores its controls and origin',await page.evaluate(()=>!document.getElementById('gait-controls').hidden&&window.athleteStudio.rig.group.parent.position.length()<1e-6))
  await page.select('#scenario','receive-pivot');await page.setViewport({width:390,height:844});await page.evaluate(()=>{window.athleteStudio.pause();window.athleteStudio.seek(1.4);document.getElementById('stage').scrollIntoView()})
  check('Mobile preview stays within the page width',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:out+'/mobile.png'})
  check('No application exceptions',!errors.length,errors)
  const receipt=await page.evaluate(async()=>await(await fetch('/studio-build.json')).json());fs.writeFileSync(out+'/browser.json',JSON.stringify({checks,errors,rows,receipt},null,2));console.log(JSON.stringify({checks:checks.length,build:receipt.buildId,errors}))
}finally{await browser.close()}
