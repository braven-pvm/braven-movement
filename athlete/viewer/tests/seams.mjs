/** Close visual inspection of garment boundaries on the real animated asset. */
import {createRequire} from 'node:module'
import fs from 'node:fs'
import path from 'node:path'
const require=createRequire(path.join(process.env.BRAVEN_TACTICS_PATH,'package.json'))
const puppeteer=require('puppeteer-core')
const output=process.env.BRAVEN_ATHLETE_OUTPUT
const browser=await puppeteer.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,defaultViewport:{width:1400,height:1100}})
const page=await browser.newPage()
try{
  await page.goto(process.env.ATHLETE_URL||'http://127.0.0.1:5391/',{waitUntil:'networkidle0'})
  await page.waitForFunction(()=>!!window.athleteStudio)
  if(process.env.HIDE_BODY)await page.evaluate(()=>window.athleteStudio.model.getObjectByName('Athlete_Body').visible=false)
  await page.evaluate(()=>{
    const s=window.athleteStudio;s.state.playing=false
    const viewport=document.getElementById('viewport')
    viewport.style.cssText='position:fixed;inset:0;width:100vw;height:100vh;z-index:9999'
    for(const el of viewport.children)if(el.tagName!=='CANVAS')el.style.display='none'
    s.controls.minDistance=.3;s.controls.enableDamping=false
  })
  fs.mkdirSync(path.join(output,'verification'),{recursive:true})
  for(const [clip,time,views] of [
    ['Ready',.4,['front','side','back','quarter']],
    ['Jog',.23,['front','side','back']],
    ['Defence',.5,['front','back']],
    ['Receive_pass',.7,['front']],
    ['Jump_reach',.55,['quarter','back']],
    ['netball_overhead_pass',1.27,['front','side','back']],
    ['netball_two_hand_snatch_pull_in',.88,['front','side']],
    ['netball_double_foot_landing',1.8,['side','back']]]){
    for(const view of views){
      await page.evaluate(({clip,time,view})=>{
        const s=window.athleteStudio
        s.playClip(clip);s.state.playing=false;s.state.time=time;s.sample()
        const angles={front:0,side:Math.PI/2,back:Math.PI,quarter:Math.PI/4}
        const a=angles[view],d=clip==='Jump_reach'?2.2:1.75
        s.controls.target.set(0,1.12,0)
        s.camera.position.set(d*Math.sin(a),1.18,d*Math.cos(a))
        s.controls.update();s.renderer.render(s.scene,s.camera)
      },{clip,time,view})
      await new Promise(r=>setTimeout(r,120))
      await page.screenshot({path:path.join(output,'verification',`seams-${process.env.HIDE_BODY?'cloth-only-':''}${clip}-${view}.png`)})
    }
  }
  console.log('Captured 19 close views across general and Movement animations.')
}finally{await browser.close()}
