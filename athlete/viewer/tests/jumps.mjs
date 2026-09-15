/** Check gravity on the real exported rig and capture take-off/landing poses. */
import {createRequire} from 'node:module'
import fs from 'node:fs'
import path from 'node:path'
import assert from 'node:assert/strict'

const require=createRequire(path.join(process.env.BRAVEN_TACTICS_PATH,'package.json'))
const output=process.env.BRAVEN_ATHLETE_OUTPUT
const candidate=process.env.MOVEMENT_CANDIDATE||output
const metadata=JSON.parse(fs.readFileSync(path.join(candidate,'movement-library.json'),'utf8'))
const browser=await require('puppeteer-core').launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,defaultViewport:{width:1440,height:1100}})
const report={assetSha256:metadata.assetSha256,checks:[],clips:[],errors:[]}
const check=(label,value)=>{assert(value,label);report.checks.push(label)}
try{
  const page=await browser.newPage()
  page.on('pageerror',error=>report.errors.push(String(error)))
  if(process.env.MOVEMENT_CANDIDATE){
    await page.setRequestInterception(true)
    page.on('request',request=>{
      const name=request.url().split('/').at(-1).split('?')[0]
      if(['netball-athlete.glb','movement-library.json'].includes(name))request.respond({status:200,contentType:name.endsWith('glb')?'model/gltf-binary':'application/json',body:fs.readFileSync(path.join(candidate,name))})
      else request.continue()
    })
  }
  await page.goto(process.env.ATHLETE_URL||'http://127.0.0.1:5393/',{waitUntil:'networkidle0'})
  await page.waitForFunction(()=>window.athleteStudio)
  fs.mkdirSync(path.join(output,'verification/jumps'),{recursive:true})
  for(const item of metadata.gravityCorrections){
    await page.select('#clip',item.clip)
    const sample=time=>page.evaluate(time=>{
      const app=window.athleteStudio;app.state.playing=false;app.state.time=time;app.sample()
      const pos=name=>app.bones.get(name).getWorldPosition(app.model.position.clone())
      return{height:pos('pelvis').y/app.model.scale.y,foot:Math.min(pos('foot_l').y,pos('foot_r').y)/app.model.scale.y}
    },time)
    const flight=item.touchdownSeconds-item.takeoffSeconds
    const values=[]
    for(const fraction of [.2,.5,.8])values.push(await sample(item.takeoffSeconds+fraction*flight))
    const acceleration=(values[2].height-2*values[1].height+values[0].height)/(.3*flight)**2
    check(`${item.clip}: exported pelvis retains gravity`,Math.abs(acceleration+9.81)<.25)
    const floor=(await sample(0)).foot
    let minimum=0,maximum=0
    const duration=await page.evaluate(()=>{const a=window.athleteStudio;return a.clips.find(c=>c.name===a.state.clip).duration})
    for(let i=0;i<=90;i++){
      const clearance=(await sample(duration*i/90)).foot-floor
      minimum=Math.min(minimum,clearance);maximum=Math.max(maximum,clearance)
    }
    check(`${item.clip}: feet stay above the floor`,minimum>-.003)
    check(`${item.clip}: short airborne phase remains visible`,flight<.65&&maximum>.05)
    report.clips.push({clip:item.clip,flightSeconds:flight,verticalAccelerationMPerS2:acceleration,minimumAnkleClearanceM:minimum,peakAnkleClearanceM:maximum})
    for(const [phase,time] of [['takeoff',item.takeoffSeconds],['apex',item.takeoffSeconds+flight*.5],['landing',item.touchdownSeconds],['absorb',item.touchdownSeconds+.13]]){
      await sample(time)
      await page.evaluate(()=>{const a=window.athleteStudio;a.controls.enableDamping=false;a.controls.target.set(0,1,.05);a.camera.position.set(2.65,1.9,4.15);a.controls.update();a.renderer.render(a.scene,a.camera)})
      await page.screenshot({path:path.join(output,'verification/jumps',`${item.clip}-${phase}.png`)})
    }
  }
  check('No browser JavaScript errors',report.errors.length===0)
  fs.writeFileSync(path.join(output,'jump-browser-verification.json'),JSON.stringify(report,null,2))
  console.log(JSON.stringify(report,null,2))
}finally{await browser.close()}
