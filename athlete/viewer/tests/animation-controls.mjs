/** Verify user selection, real skinned balls and deterministic held-ball presentation. */
import {createRequire} from 'node:module'
import fs from 'node:fs'
import path from 'node:path'
import assert from 'node:assert/strict'
const require=createRequire(path.join(process.env.BRAVEN_TACTICS_PATH||'F:/Repositories/braven-tactics-netball-athlete','package.json'))
const browser=await require('puppeteer-core').launch({executablePath:process.env.CHROME_PATH||'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,defaultViewport:{width:1440,height:1000}})
const out=path.resolve('verification/animation-controls');fs.mkdirSync(out,{recursive:true})
const page=await browser.newPage(),checks=[],errors=[],measurements={}
const check=(name,value)=>{checks.push({name,passed:!!value});assert(value,name)}
page.on('pageerror',e=>errors.push(String(e)))
try{
  await page.goto(process.env.STUDIO_URL||'http://127.0.0.1:5397/',{waitUntil:'networkidle0'});await page.waitForFunction(()=>window.bravenStudio)
  check('Startup remains paused',await page.evaluate(()=>!window.athleteStudio.state.playing))
  const clips=await page.evaluate(()=>window.athleteStudio.clips.map(c=>c.name))
  for(const clip of clips){
    await page.evaluate(()=>window.athleteStudio.pause());await page.select('#clip',clip)
    check(`${clip}: dropdown starts playback`,await page.evaluate(()=>window.athleteStudio.state.playing))
    const needsBall=clip.startsWith('netball_')||clip==='Receive_pass'
    check(`${clip}: ball matches movement`,await page.evaluate(expected=>{
      const a=window.athleteStudio,source=a.movementLibrary.techniques.find(t=>t.clip===a.state.clip)
      a.pause();a.seek(source?source.contactFrame/source.fps+.01:a.duration()*.4)
      return a.model.getObjectByName('Movement_Ball').visible===expected&&(!expected||a.bones.get('Ball_Control').scale.x>.9)
    },needsBall))
  }
  await page.emulateMediaFeatures([{name:'prefers-reduced-motion',value:'reduce'}])
  await page.$eval('#speed',el=>{el.value=.75;el.dispatchEvent(new Event('input',{bubbles:true}))})
  await page.click('[data-animation="netball_chest_pass"]')
  check('Explicit library selection plays with reduced-motion preference and preserves chosen speed',await page.evaluate(()=>window.athleteStudio.state.playing&&window.athleteStudio.state.speed===.75))
  await page.click('[data-animation="Receive_pass"]')
  await page.evaluate(()=>{const a=window.athleteStudio;a.pause();a.seek(.9);a.view('front')})
  await page.screenshot({path:path.join(out,'receive-pass.png')})
  check('Receive and pass includes actual incoming and outgoing flight',await page.evaluate(()=>{
    const a=window.athleteStudio,b=a.bones.get('Ball_Control'),point=t=>{a.seek(t);return b.getWorldPosition(a.model.position.clone())}
    return point(0).distanceTo(point(.9))>.3&&point(a.duration()-.001).distanceTo(point(a.duration()-.35))>.5
  }))
  for(const time of [1.5,2.6]){
    await page.evaluate(t=>{const a=window.athleteStudio;a.seek(t);a.view('quarter')},time)
    await page.screenshot({path:path.join(out,`receive-pass-${time}.png`)})
  }
  const skin=await page.evaluate(()=>{
    const a=window.athleteStudio;let ball
    a.model.getObjectByName('Movement_Ball').traverse(o=>{if(o.isSkinnedMesh&&o.material.name==='Movement_Ball')ball=o})
    let largestStep=0,previous
    for(let i=0;i<=30;i++){
      a.seek(1.4+i/100);ball.skeleton.update()
      const center=a.bones.get('Ball_Control').getWorldPosition(a.model.position.clone()),vertex=center.clone()
      ball.getVertexPosition(0,vertex).applyMatrix4(ball.matrixWorld)
      if(vertex.distanceTo(center)<.1)return {rendered:false}
      if(previous)largestStep=Math.max(largestStep,center.distanceTo(previous));previous=center
    }
    return {rendered:true,largestStep}
  })
  measurements.receivePassJoin=skin
  check('The joined sequence renders a full-size skinned ball without a teleport at the transition',skin.rendered&&skin.largestStep<.03)
  await page.select('#driver','tactics');await page.click('#carry')
  const cadence=await page.evaluate(()=>{
    const a=window.athleteStudio,result={}
    for(const gait of ['walk','run','sprint']){
      a.state.gait=gait;const b=a.rig.bone.calf_l,rest=a.rig.bind.get(b).local,angles=[]
      for(let i=0;i<=480;i++){a.state.time=i/120;a.sample();angles.push(b.quaternion.angleTo(rest))}
      // Count complete knee-flexion pulses, not floating-point noise on the
      // planted half-cycle's flat values.
      const min=Math.min(...angles),range=Math.max(...angles)-min,low=min+range*.25,high=min+range*.75
      let armed=angles[0]<low,count=0
      for(const angle of angles){if(angle<low)armed=true;else if(armed&&angle>high){count++;armed=false}}
      result[gait]=count
    }
    return result
  })
  check('Walking, running and sprinting complete four, six and eight strides in four seconds',cadence.walk===4&&cadence.run===6&&cadence.sprint===8)
  measurements.stridesPerFourSeconds=cadence
  for(const height of [1.6,1.75,1.95]){
    await page.$eval('#height',(el,v)=>{el.value=v;el.dispatchEvent(new Event('input',{bubbles:true}))},height)
    for(const gait of ['static','walk','run','sprint']){
      await page.evaluate(()=>window.athleteStudio.pause());await page.select('#gait',gait)
      check(`Selecting ${gait} starts playback`,await page.evaluate(()=>window.athleteStudio.state.playing))
      const result=await page.evaluate(()=>{
        const a=window.athleteStudio,ball=a.rig.bone.Ball_Control,p=new Map()
        let maxGap=0
        for(const t of [0,.4,1.1,2.7,3.8,1.1]){
          a.seek(t)
          const center=ball.getWorldPosition(a.model.position.clone()),radius=.11*a.state.height/1.7216965637645487
          for(const side of ['l','r']){
            const wrist=a.rig.bone[`hand_${side}`].getWorldPosition(center.clone())
            const finger=a.rig.bone[`middle_01_${side}`].getWorldPosition(center.clone())
            maxGap=Math.max(maxGap,Math.abs(wrist.lerp(finger,.72).distanceTo(center)-radius))
          }
          const snapshot=[...center.toArray(),...Object.values(a.rig.bone).flatMap(b=>b.quaternion.toArray())]
          if(p.has(t)&&snapshot.some((n,i)=>Math.abs(n-p.get(t)[i])>1e-6))return {deterministic:false,maxGap}
          p.set(t,snapshot)
        }
        return {visible:a.rig.group.getObjectByName('Movement_Ball').visible,scale:ball.scale.x,deterministic:true,maxGap}
      })
      check(`Carry ${gait} at ${height} m: visible ball, palms within 1 cm, deterministic scrub`,result.visible&&result.scale>.9&&result.deterministic&&result.maxGap<.01)
    }
  }
  await page.screenshot({path:path.join(out,'carry.png')})
  await page.click('#carry')
  check('Unloaded Tactics movement hides the private preview ball',await page.evaluate(()=>!window.athleteStudio.rig.group.getObjectByName('Movement_Ball').visible))
  for(const gait of ['walk','run','sprint']){
    await page.select('#gait',gait)
    check(`${gait} loop joins without a pose jump`,await page.evaluate(()=>{
      const a=window.athleteStudio;a.seek(0);const before=Object.values(a.rig.bone).map(b=>b.quaternion.clone())
      a.seek(3.999);return Object.values(a.rig.bone).every((b,i)=>b.quaternion.angleTo(before[i])<.03)
    }))
  }
  await page.select('#driver','clips');await page.select('#clip','Receive_pass')
  await page.evaluate(()=>{const a=window.athleteStudio;a.seek(.9);a.enterPose();a.bones.get('Ball_Control').position.x+=.1;a.sample()})
  const setup=await page.evaluate(()=>window.athleteStudio.captureSetup())
  await page.select('#clip','Ready');await page.evaluate(s=>window.athleteStudio.applySetup(s),setup)
  check('Restoring an edited ball pose stays paused and preserves the ball transform',await page.evaluate(s=>{
    const a=window.athleteStudio;return !a.state.playing&&a.state.poseMode&&a.bones.get('Ball_Control').position.toArray().every((n,i)=>Math.abs(n-s.pose.Ball_Control.position[i])<1e-8)
  },setup))
  check('No application exceptions',!errors.length)
}finally{
  const receipt=await page.evaluate(async()=>await(await fetch('/studio-build.json')).json()).catch(()=>null)
  fs.writeFileSync(path.join(out,process.env.CONTROLS_RECEIPT||'checks.json'),JSON.stringify({receipt,checks,measurements,errors},null,2))
  console.log(JSON.stringify({checks:checks.length,failed:checks.filter(c=>!c.passed),errors},null,2));await browser.close()
}
