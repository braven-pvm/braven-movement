/** Compare the candidate's actual skinned motion with the accepted baseline. */
import {createRequire} from 'node:module'
import fs from 'node:fs'
import path from 'node:path'
import assert from 'node:assert/strict'
const base=process.env.BRAVEN_ATHLETE_SOURCE||'E:/cloud services/OneDrive - About IT Group (Pty) Ltd/Documents/ChatGPT/Braven Movement/Netball Athlete'
const candidate=process.env.MOVEMENT_CANDIDATE||path.join(base,'candidates/07-realism')
const metadata=JSON.parse(fs.readFileSync(path.join(candidate,'movement-library.json')))
const require=createRequire(path.join(process.env.BRAVEN_TACTICS_PATH||'F:/Repositories/braven-tactics-netball-athlete','package.json'))
const browser=await require('puppeteer-core').launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,defaultViewport:{width:1440,height:1000}})
const out=path.resolve('verification/realism');fs.mkdirSync(out,{recursive:true})
const checks=[],metrics=[],errors=[]
const check=(name,ok,detail)=>{checks.push({name,ok,detail});assert(ok,`${name}: ${JSON.stringify(detail)}`)}
async function open(dir){
  const page=await browser.newPage();page.on('pageerror',e=>errors.push(String(e)))
  await page.setRequestInterception(true)
  page.on('request',r=>{const name=r.url().split('/athlete-assets/')[1]?.split('?')[0]
    if(['netball-athlete.glb','movement-library.json','manifest.json'].includes(name))r.respond({status:200,contentType:name.endsWith('glb')?'model/gltf-binary':'application/json',body:fs.readFileSync(path.join(dir,name))})
    else r.continue()
  })
  await page.goto(process.env.STUDIO_URL||'http://127.0.0.1:5397/',{waitUntil:'networkidle0'});await page.waitForFunction(()=>window.bravenStudio);return page
}
try{
  const old=await open(base),page=await open(candidate)
  for(const t of metadata.techniques){
    await page.select('#clip',t.clip);await old.select('#clip',t.clip)
    const d=t.ballDynamics
    const result=await page.evaluate(({clip,d})=>{
      const a=window.athleteStudio;a.playClip(clip);a.state.playing=false
      const at=t=>{a.seek(t);return a.bones.get('Ball_Control').getWorldPosition(a.model.position.clone())}
      const result={}
      if(d.incomingStartSeconds!==null){
        const start=d.incomingStartSeconds,flight=d.contactSeconds-start,dt=flight*.2
        const x=at(start+flight*.3),y=at(start+flight*.5),z=at(start+flight*.7)
        result.gravity=(z.y-2*y.y+x.y)/(dt*dt)
        result.horizontalAcceleration=Math.hypot(z.x-2*y.x+x.x,z.z-2*y.z+x.z)/(dt*dt)
        at(start*.5);result.hiddenBefore=a.bones.get('Ball_Control').scale.x===0
        at(d.contactSeconds+.01);result.visibleOnContact=a.bones.get('Ball_Control').scale.x>.99
        result.contactGap=at(d.contactSeconds-.001).distanceTo(at(d.contactSeconds+.001))
      }
      if(d.outgoing){
        const start=(Math.ceil(d.outgoing.start*60)+1)/60,dt=1/60,x=at(start),y=at(start+dt),z=at(start+dt*2)
        result.outgoingGravity=(z.y-2*y.y+x.y)/(dt*dt)
        result.horizontalSpeed=Math.hypot(z.x-x.x,z.z-x.z)/(dt*2)
      }
      if(d.outgoing?.bounceSeconds){
        const impact=d.outgoing.bounceSeconds
        result.bounceHeight=at(impact).y
        result.beforeBounce=at(impact-.03).y
        result.afterBounce=at(impact+.03).y
        result.bounceIncluded=a.duration()>impact+.2
      }
      return result
    },{clip:t.clip,d})
    metrics.push({clip:t.clip,...result})
    if(d.incomingStartSeconds!==null){
      check(`${t.clip}: incoming ball has gravity independent of body/jump timing`,Math.abs(result.gravity+9.81)<.35&&result.horizontalAcceleration<.35,result)
      check(`${t.clip}: no unsupported hovering before throw, visible at contact`,result.hiddenBefore&&result.visibleOnContact)
      check(`${t.clip}: flight joins the grip continuously`,result.contactGap<.025,result.contactGap)
    }
    if(d.outgoing)check(`${t.clip}: outgoing flight retains gravity`,Math.abs(result.outgoingGravity+9.81)<.6,result.outgoingGravity)
    if(d.outgoing?.bounceSeconds)check('Bounce pass visibly strikes the floor and rebounds within the clip',result.bounceIncluded&&result.bounceHeight>.09&&result.bounceHeight<.16&&result.beforeBounce>result.bounceHeight+.03&&result.afterBounce>result.bounceHeight+.03,result)
    if(d.catchAbsorption){
      const sample=async(p,time)=>p.evaluate(({clip,time})=>{
        const a=window.athleteStudio;a.playClip(clip);a.seek(time)
        return Object.fromEntries(['pelvis','foot_l','foot_r','hand_l','hand_r','Ball_Control'].map(n=>[n,a.bones.get(n).getWorldPosition(a.model.position.clone()).toArray()]))
      },{clip:t.clip,time})
      const time=d.contactSeconds+d.catchAbsorption.peakSeconds,before=await sample(old,time),after=await sample(page,time)
      const distance=(x,y)=>Math.hypot(...x.map((n,i)=>n-y[i]))
      const footError=Math.max(...['l','r'].map(s=>distance(before['foot_'+s],after['foot_'+s])))
      const drop=before.pelvis[1]-after.pelvis[1]
      check(`${t.clip}: catch absorbs through the body with planted feet`,drop>.02&&drop<.04&&footError<.002,{drop,footError})
      // Both hands can be compared on two-hand catches; one-hand variants have
      // an intentionally free hand until the source says it joins.
      if(t.clip.includes('two_hand')){
        const gap=Math.max(...['l','r'].map(s=>distance(before['hand_'+s].map((n,i)=>n-before.Ball_Control[i]),after['hand_'+s].map((n,i)=>n-after.Ball_Control[i]))))
        check(`${t.clip}: hands and ball give together at impact`,gap<.004,gap)
      }
      await page.evaluate(()=>window.athleteStudio.view('quarter'))
      await page.screenshot({path:path.join(out,`${t.clip}-absorb.png`)})
    }
  }
  await page.select('#clip','netball_bounce_pass')
  await page.evaluate(()=>{const a=window.athleteStudio;const d=a.movementLibrary.techniques.find(t=>t.clip===a.state.clip).ballDynamics;a.seek(d.outgoing.bounceSeconds);a.camera.position.set(5,2.5,6);a.controls.target.set(0,.8,1.3);a.controls.update()})
  await page.screenshot({path:path.join(out,'bounce-impact.png')})
  check('No browser application exceptions',!errors.length,errors)
}finally{
  fs.writeFileSync(path.join(out,'candidate.json'),JSON.stringify({assetSha256:metadata.assetSha256,checks,metrics,errors},null,2))
  console.log(JSON.stringify({passed:checks.filter(c=>c.ok).length,failed:checks.filter(c=>!c.ok),metrics,errors},null,2));await browser.close()
}
