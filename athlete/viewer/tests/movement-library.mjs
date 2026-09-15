/** Exercise the actual exported Movement clips, including the animated ball. */
import {createRequire} from 'node:module'
import fs from 'node:fs'
import path from 'node:path'
import assert from 'node:assert/strict'
const require=createRequire(path.join(process.env.BRAVEN_TACTICS_PATH,'package.json'))
const output=process.env.BRAVEN_ATHLETE_OUTPUT
const candidate=process.env.MOVEMENT_CANDIDATE||output
const metadata=JSON.parse(fs.readFileSync(path.join(candidate,'movement-library.json'),'utf8'))
const browser=await require('puppeteer-core').launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,defaultViewport:{width:1440,height:1100}})
const errors=[],report={assetSha256:metadata.assetSha256,clips:[],checks:[],errors}
try{
  const page=await browser.newPage()
  const downloadDir=fs.mkdtempSync(path.join(output,'verification/movement-pose-'))
  const cdp=await page.createCDPSession()
  await cdp.send('Page.setDownloadBehavior',{behavior:'allow',downloadPath:downloadDir})
  page.on('pageerror',e=>errors.push(String(e)))
  if(process.env.MOVEMENT_CANDIDATE){
    await page.setRequestInterception(true)
    page.on('request',request=>{
      const name=request.url().split('/').at(-1).split('?')[0]
      if(['netball-athlete.glb','movement-library.json'].includes(name))
        request.respond({status:200,contentType:name.endsWith('glb')?'model/gltf-binary':'application/json',body:fs.readFileSync(path.join(candidate,name))})
      else request.continue()
    })
  }
  await page.goto(process.env.ATHLETE_URL||'http://127.0.0.1:5391/',{waitUntil:'networkidle0'})
  await page.waitForFunction(()=>!!window.athleteStudio)
  const info=await page.evaluate(()=>window.athleteStudio.info())
  assert.equal(info.boneCount,70)
  assert.equal(info.clips.length,5+metadata.techniques.length)
  const check=(label,value)=>{assert(value,label);report.checks.push(label)}
  check('Source review groups match the imported manifest',await page.$$eval('#clip optgroup',groups=>groups.map(g=>g.children.length).join(','))===`${metadata.techniques.filter(t=>t.sourceChecksPassed).length},${metadata.techniques.filter(t=>!t.sourceChecksPassed).length},5`)
  const first=metadata.techniques.find(t=>t.clip===metadata.defaultClip)||metadata.techniques[0]
  await page.select('#clip',first.clip)
  await page.click('#phase-buttons button:nth-child(2)')
  check('Named phase button pauses at the exact source time',await page.evaluate(time=>!window.athleteStudio.state.playing&&Math.abs(window.athleteStudio.state.time-time)<1e-5,first.phases[1].time))
  await page.click('#loop')
  await page.evaluate(()=>{const s=window.athleteStudio;s.state.time=s.clips.find(c=>c.name===s.state.clip).duration-.05;s.state.playing=true})
  await page.waitForFunction(()=>!window.athleteStudio.state.playing)
  check('One-shot playback stops at the end',await page.evaluate(()=>{const s=window.athleteStudio;return s.state.time>s.clips.find(c=>c.name===s.state.clip).duration-.003}))
  await page.click('#play')
  check('Play restarts a completed one-shot clip',await page.evaluate(()=>window.athleteStudio.state.playing&&window.athleteStudio.state.time<.5))
  await page.click('#loop')
  await page.select('#clip','Ready')
  check('General clips hide the technique ball',await page.evaluate(()=>!window.athleteStudio.model.getObjectByName('Movement_Ball').visible))
  await page.select('#driver','tactics')
  check('Tactics preview hides the technique ball',await page.evaluate(()=>!window.athleteStudio.rig.group.getObjectByName('Movement_Ball').visible))
  await page.select('#driver','clips')
  fs.mkdirSync(path.join(output,'verification/movement-library'),{recursive:true})
  for(const item of metadata.techniques){
    const sample=async(time)=>page.evaluate(({clip,time})=>{
      const s=window.athleteStudio;s.playClip(clip);s.state.playing=false;s.state.time=time;s.sample()
      let ball;s.model.getObjectByName('Movement_Ball').traverse(o=>{if(o.isSkinnedMesh&&o.material.name==='Movement_Ball')ball=o});ball.skeleton.update()
      const point=s.model.position.clone();ball.getVertexPosition(0,point).applyMatrix4(ball.matrixWorld)
      const hand=s.bones.get('hand_l').getWorldPosition(s.model.position.clone())
      const sum=s.model.position.clone().set(0,0,0),p=sum.clone()
      for(let i=0;i<ball.geometry.attributes.position.count;i++){ball.getVertexPosition(i,p).applyMatrix4(ball.matrixWorld);sum.add(p)}
      sum.divideScalar(ball.geometry.attributes.position.count)
      const center=s.bones.get('Ball_Control').getWorldPosition(p)
      return{ball:point.toArray(),hand:hand.toArray(),scale:s.bones.get('Ball_Control').scale.toArray(),ballCenterError:sum.distanceTo(center)}
    },{clip:item.clip,time})
    const start=item.ballDynamics?.incomingStartSeconds!=null?item.ballDynamics.incomingStartSeconds+.035:0
    const a=await sample(start),b=await sample(item.seconds*.85),repeat=await sample(start)
    const distance=(x,y)=>Math.hypot(...x.map((v,i)=>v-y[i]))
    assert(distance(a.ball,b.ball)>.015,`${item.clip}: ball moves`)
    assert(distance(a.hand,b.hand)>.005,`${item.clip}: hand moves`)
    assert(distance(a.ball,repeat.ball)<1e-5,`${item.clip}: deterministic ball`)
    assert(a.scale.every(v=>Math.abs(v-1)<1e-5))
    assert(a.ballCenterError<.005&&b.ballCenterError<.005,`${item.clip}: ball surface follows its control`)
    const end=await sample(item.seconds),nearEnd=await sample(item.seconds-.002)
    assert(distance(end.ball,nearEnd.ball)<.05,`${item.clip}: scrubbing to the end holds the final frame at the current throw speed`)
    report.clips.push({clip:item.clip,ballDisplacementM:distance(a.ball,b.ball),handDisplacementM:distance(a.hand,b.hand)})
    const chosen=[item.phases[0],item.phases.find(p=>p.name==='contact')||item.phases.find(p=>p.name==='release')||item.phases[1],item.phases.find(p=>['pull_in','control','drive'].includes(p.name))||item.phases.at(-1)]
    for(const phase of chosen){
      await sample(phase.time)
      await page.evaluate(()=>{
        const s=window.athleteStudio;s.controls.enableDamping=false;s.controls.target.set(0,.95,.2)
        s.camera.position.set(2.8,1.85,4.2);s.controls.update();s.renderer.render(s.scene,s.camera)
      })
      await page.screenshot({path:path.join(output,'verification/movement-library',`${item.clip}-${phase.name}.png`)})
    }
  }
  await page.select('#clip',first.clip)
  await page.click('#phase-buttons button:nth-child(2)')
  await page.click('[data-tab="pose"]')
  await page.select('#bone','Ball_Control')
  await page.$eval('#px',el=>{el.value='.12';el.dispatchEvent(new Event('input',{bubbles:true}))})
  const editedBall=await page.evaluate(()=>window.athleteStudio.bones.get('Ball_Control').position.toArray())
  await page.click('#save-pose')
  const posePath=path.join(downloadDir,'braven-athlete-pose.json')
  for(let i=0;i<100&&!fs.existsSync(posePath);i++)await new Promise(r=>setTimeout(r,100))
  const saved=JSON.parse(fs.readFileSync(posePath,'utf8'))
  check('Pose file retains the ball position and scale',saved.clip===first.clip&&saved.bones.Ball_Control.scale.every(v=>Math.abs(v-1)<1e-5))
  await page.evaluate(()=>window.athleteStudio.playClip('Ready'))
  await(await page.$('#pose-file')).uploadFile(posePath)
  await page.waitForFunction(()=>document.getElementById('pose-message').textContent==='Pose loaded.')
  const loaded=await page.evaluate(()=>{const s=window.athleteStudio;return{clip:s.state.clip,position:s.bones.get('Ball_Control').position.toArray(),visible:s.model.getObjectByName('Movement_Ball').visible}})
  check('Edited ball pose loads visibly after switching to a general clip',loaded.clip===first.clip&&loaded.visible&&loaded.position.every((v,i)=>Math.abs(v-editedBall[i])<1e-5))
  assert.deepEqual(errors,[])
  fs.writeFileSync(path.join(output,'movement-browser-verification.json'),JSON.stringify(report,null,2))
  console.log(JSON.stringify(report,null,2))
}finally{await browser.close()}
