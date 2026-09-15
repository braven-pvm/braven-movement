/** Measure possession-aware flight windows on the rendered, retargeted athlete. */
import {createRequire} from 'node:module'
import fs from 'node:fs'
import path from 'node:path'
const assets=process.env.BRAVEN_ATHLETE_SOURCE||'E:/cloud services/OneDrive - About IT Group (Pty) Ltd/Documents/ChatGPT/Braven Movement/Netball Athlete'
const library=JSON.parse(fs.readFileSync(path.join(assets,'movement-library.json')))
const map=(frame,anchors)=>{
  if(!anchors)return frame
  for(let i=1;i<anchors.length;i++)if(frame<=anchors[i][0]){const [a,b]=anchors[i-1],[c,d]=anchors[i];return b+(frame-a)/(c-a)*(d-b)}
  return anchors.at(-1)[1]+frame-anchors.at(-1)[0]
}
const cases=library.techniques.map(t=>{
  const ball=JSON.parse(fs.readFileSync(path.join(assets,'movement-library/source/spikes/movements',t.clip+'.ball.json')))
  const original=t.sourceTiming||t
  return {clip:t.clip,contact:t.contactFrame/t.fps,release:t.releaseFrame==null?null:t.releaseFrame/t.fps,
    incoming:ball.release?.atPhase>0?map(ball.release.atPhase*(original.frameCount-1),t.sourceFrameMap)/t.fps:null}
})
const require=createRequire(path.join(process.env.BRAVEN_TACTICS_PATH||'F:/Repositories/braven-tactics-netball-athlete','package.json'))
const browser=await require('puppeteer-core').launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,defaultViewport:{width:1440,height:1000}})
const page=await browser.newPage(),errors=[];page.on('pageerror',e=>errors.push(String(e)))
try{
  await page.goto(process.env.STUDIO_URL||'http://127.0.0.1:5397/',{waitUntil:'networkidle0'});await page.waitForFunction(()=>window.bravenStudio)
  const results=[]
  for(const item of cases)results.push(await page.evaluate(item=>{
    const a=window.athleteStudio;a.playClip(item.clip);a.state.playing=false
    const point=(name,t)=>{a.seek(t);return a.bones.get(name).getWorldPosition(a.model.position.clone())}
    const ball=t=>point('Ball_Control',t),velocity=t=>ball(t+.01).sub(ball(t-.01)).divideScalar(.02).toArray()
    const acceleration=t=>ball(t+.02).add(ball(t-.02)).addScaledVector(ball(t),-2).divideScalar(.0004).toArray()
    const incomingMid=item.incoming==null?null:(item.incoming+item.contact)/2
    return {...item,seconds:a.duration(),incomingVelocity:incomingMid==null?null:velocity(incomingMid),
      incomingAcceleration:incomingMid==null?null:acceleration(incomingMid),
      contactBall:ball(item.contact).toArray(),velocityBefore:velocity(item.contact-.025),velocityAfter:velocity(item.contact+.025),
      pelvisAfter:[0,.05,.1,.2,.3].map(t=>point('pelvis',Math.min(a.duration()-.01,item.contact+t)).toArray())}
  },item))
  const receipt=await page.evaluate(async()=>await(await fetch('/studio-build.json')).json())
  const out=path.resolve('verification/realism');fs.mkdirSync(out,{recursive:true})
  fs.writeFileSync(path.join(out,process.env.REALISM_RECEIPT||'before.json'),JSON.stringify({receipt,results,errors},null,2))
  console.log(JSON.stringify(results.map(({clip,incoming,incomingVelocity,incomingAcceleration,velocityAfter})=>({clip,incoming,incomingVelocity,incomingAcceleration,velocityAfter})),null,2))
}finally{await browser.close()}
