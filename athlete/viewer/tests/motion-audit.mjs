/** Read the actual rendered clip clocks and ball trajectories; retain per-clip evidence. */
import {createRequire} from 'node:module'
import fs from 'node:fs'
import path from 'node:path'
import assert from 'node:assert/strict'
const require=createRequire(path.join(process.env.BRAVEN_TACTICS_PATH||'F:/Repositories/braven-tactics-netball-athlete','package.json'))
const browser=await require('puppeteer-core').launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,defaultViewport:{width:1440,height:1000}})
const out=path.resolve('verification/motion-audit');fs.mkdirSync(out,{recursive:true})
const page=await browser.newPage(),errors=[];page.on('pageerror',e=>errors.push(String(e)))
try{
  await page.goto(process.env.STUDIO_URL||'http://127.0.0.1:5397/',{waitUntil:'networkidle0'})
  await page.waitForFunction(()=>window.bravenStudio)
  await page.evaluate(()=>window.athleteStudio.pause());await page.select('#clip','Receive_pass')
  const dropdownAutoplay=await page.evaluate(()=>window.athleteStudio.state.playing)
  const clips=await page.evaluate(()=>window.athleteStudio.clips.map(c=>({name:c.name,duration:c.duration}))),audit=[]
  for(const clip of clips){
    await page.select('#clip',clip.name)
    const measured=await page.evaluate(async()=>{
      const app=window.athleteStudio
      document.getElementById('speed').value=1;document.getElementById('speed').dispatchEvent(new Event('input',{bubbles:true}))
      app.state.playing=true;app.state.loop=true
      return new Promise(resolve=>{
        let start,lastTime,advanced=0,frames=0
        function measure(now){
          if(start===undefined){start=now;lastTime=app.state.time}
          else{let dt=app.state.time-lastTime;if(dt<0)dt+=app.duration();advanced+=dt;lastTime=app.state.time;frames++}
          if(now-start>=850){app.pause();resolve({wallSeconds:(now-start)/1000,animationSeconds:advanced,observedSpeed:advanced/((now-start)/1000),renderedFps:frames/((now-start)/1000)});return}
          requestAnimationFrame(measure)
        }requestAnimationFrame(measure)
      })
    })
    const geometry=await page.evaluate(()=>{
      const app=window.athleteStudio,source=app.movementLibrary.techniques.find(t=>t.clip===app.state.clip),duration=app.duration()
      const point=name=>app.bones.get(name)?.getWorldPosition(app.model.position.clone()).toArray()
      const sample=t=>{app.state.time=t;app.sample();return {t,ball:point('Ball_Control'),hands:['hand_l','hand_r','middle_01_l','middle_01_r'].map(point),scale:app.bones.get('Ball_Control').scale.toArray()}}
      const points=[sample(0),sample(duration*.25),sample(duration*.5),sample(duration*.75),sample(duration-.001)]
      const contact=source?source.contactFrame/source.fps:null,release=source?.releaseFrame==null?null:source.releaseFrame/source.fps
      const flights=[]
      // Use explicit launch/contact states; whole pre-contact windows include
      // the external feeder's holding period and are not flight measurements.
      const incoming=source?.ballDynamics?.incomingStartSeconds
      const impact=source?.ballDynamics?.outgoing?.bounceSeconds
      for(const [label,start,end] of [['incoming-flight',incoming,contact],['outgoing-flight',release,impact??duration],['rebound',impact,duration]]){
        if(start==null||end==null||end-start<.075)continue
        const a=sample(start+(end-start)*.2),b=sample(start+(end-start)*.5),c=sample(start+(end-start)*.8),dt=(end-start)*.3
        flights.push({label,seconds:end-start,meanSpeedMps:Math.hypot(...a.ball.map((v,i)=>c.ball[i]-v))/(dt*2),verticalAccelerationMps2:(c.ball[1]-2*b.ball[1]+a.ball[1])/(dt*dt)})
      }
      return {visible:app.model.getObjectByName('Movement_Ball').visible,points,contact,release,flights,sourceSeconds:source?.seconds??null}
    })
    audit.push({...clip,...measured,...geometry})
    if(['Receive_pass','Jump_reach'].includes(clip.name)){
      await page.evaluate(()=>{const a=window.athleteStudio;a.state.time=a.duration()*.5;a.sample()})
      await page.screenshot({path:path.join(out,clip.name+'.png')})
    }
  }
  const receipt=await page.evaluate(async()=>await(await fetch('/studio-build.json')).json())
  const result={receipt,dropdownAutoplay,audit,errors}
  fs.writeFileSync(path.join(out,process.env.AUDIT_NAME||'audit.json'),JSON.stringify(result,null,2))
  console.log(JSON.stringify({dropdownAutoplay,clocks:audit.map(c=>({clip:c.name,speed:c.observedSpeed,duration:c.duration,visible:c.visible,flights:c.flights})),errors},null,2))
  assert(audit.every(c=>Math.abs(c.observedSpeed-1)<.025),'Every animation must retain real-time playback at 1x')
  assert.equal(errors.length,0,'No application exceptions during the audit')
}finally{await browser.close()}
