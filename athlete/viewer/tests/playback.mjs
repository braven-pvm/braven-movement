/** Measure the real preview clock against wall time, including slow rendering. */
import {createRequire} from 'node:module'
import fs from 'node:fs'
import path from 'node:path'
import assert from 'node:assert/strict'

const require=createRequire(path.join(process.env.BRAVEN_TACTICS_PATH,'package.json'))
const output=process.env.BRAVEN_ATHLETE_OUTPUT
const browser=await require('puppeteer-core').launch({
  executablePath:process.env.CHROME_PATH||'C:/Program Files/Google/Chrome/Application/chrome.exe',
  headless:true,defaultViewport:{width:1440,height:1000},
})
const report={checks:[],timing:[],errors:[]}
const check=(label,condition)=>{assert(condition,label);report.checks.push(label)}
try{
  const page=await browser.newPage()
  page.on('pageerror',error=>report.errors.push(String(error)))
  await page.goto(process.env.ATHLETE_URL||'http://127.0.0.1:5393/',{waitUntil:'networkidle0'})
  await page.waitForFunction(()=>window.athleteStudio)
  for(const speed of [1,.5,2]){
    const measured=await page.evaluate(async speed=>{
      const app=window.athleteStudio
      app.playClip('netball_chest_pass');app.state.playing=true;app.state.loop=true
      const slider=document.getElementById('speed');slider.value=speed
      slider.dispatchEvent(new Event('input',{bubbles:true}))
      const duration=app.clips.find(c=>c.name===app.state.clip).duration
      return new Promise(resolve=>{
        let start,lastTime,advanced=0,frames=0,previous;const intervals=[]
        function measure(now){
          if(start===undefined){start=now;lastTime=app.state.time;previous=now}
          else{
            let step=app.state.time-lastTime;if(step<0)step+=duration
            advanced+=step;lastTime=app.state.time;frames++;intervals.push(now-previous);previous=now
          }
          if(now-start>=2200){
            app.state.playing=false
            const wall=(now-start)/1000
            resolve({speed,wallSeconds:wall,animationSeconds:advanced,observedSpeed:advanced/wall,
              fps:frames/wall,slowFrames:intervals.filter(ms=>ms>80).length})
            return
          }
          // Rendering may miss deadlines. Animation time must still keep up.
          const until=performance.now()+120;while(performance.now()<until){}
          requestAnimationFrame(measure)
        }
        requestAnimationFrame(measure)
      })
    },speed)
    report.timing.push(measured)
    check(`${speed}x playback retains wall time through slow frames`,Math.abs(measured.observedSpeed-speed)<.025)
    check(`${speed}x test exercised frames slower than 80 ms`,measured.slowFrames>=10)
  }
  await page.evaluate(()=>{
    const app=window.athleteStudio;app.playClip('Ready');app.state.playing=false;app.sample()
    document.getElementById('speed').value=1
    document.getElementById('speed').dispatchEvent(new Event('input',{bubbles:true}))
  })
  await page.click('#play')
  await page.waitForFunction(()=>window.athleteStudio.state.time>.2)
  await page.click('#play')
  const paused=await page.evaluate(()=>window.athleteStudio.state.time)
  await new Promise(resolve=>setTimeout(resolve,350))
  check('Pause keeps the playhead fixed',await page.evaluate(time=>window.athleteStudio.state.time===time,paused))
  await page.$eval('#timeline',el=>{el.value=.4;el.dispatchEvent(new Event('input',{bubbles:true}))})
  check('Scrubbing stays paused at the selected time',await page.evaluate(()=>!window.athleteStudio.state.playing&&Math.abs(window.athleteStudio.state.time-.4)<1e-5))
  await page.click('#play')
  check('Resume starts from the scrubbed frame',await page.evaluate(()=>window.athleteStudio.state.playing&&window.athleteStudio.state.time>=.4&&window.athleteStudio.state.time<.65))
  // Exercise browser visibility events without switching the user's active tab.
  const hidden=await page.evaluate(async()=>{
    Object.defineProperty(document,'hidden',{configurable:true,get:()=>true})
    document.dispatchEvent(new Event('visibilitychange'))
    const app=window.athleteStudio,before=app.state.time
    await new Promise(resolve=>setTimeout(resolve,400))
    const during=app.state.time
    delete document.hidden
    document.dispatchEvent(new Event('visibilitychange'))
    const resumedAt=performance.now()
    // A slow first visible frame is active time and must not be mistaken for
    // the hidden period that the viewer intentionally excludes.
    const until=resumedAt+180;while(performance.now()<until){}
    const first=await new Promise(resolve=>requestAnimationFrame(now=>resolve({time:app.state.time,now})))
    return{before,during,after:first.time,expectedAdvance:Math.max(0,(first.now-resumedAt)/1000)*app.state.speed}
  })
  report.visibility=hidden
  check('Hidden time is excluded while the first visible frame retains its elapsed time',hidden.before===hidden.during&&Math.abs(hidden.after-hidden.before-hidden.expectedAdvance)<.025)
  check('No browser JavaScript errors',report.errors.length===0)
  report.studioScripts=await page.evaluate(async()=>Promise.all([...document.querySelectorAll('script[src]')].map(async script=>({
    url:script.src,sha256:[...new Uint8Array(await crypto.subtle.digest('SHA-256',await(await fetch(script.src)).arrayBuffer()))].map(b=>b.toString(16).padStart(2,'0')).join(''),
  }))))
  report.assetSha256=JSON.parse(fs.readFileSync(path.join(output,'manifest.json'),'utf8')).files['netball-athlete.glb'].sha256
  fs.writeFileSync(path.join(output,'playback-verification.json'),JSON.stringify(report,null,2))
  console.log(JSON.stringify(report,null,2))
}finally{await browser.close()}
