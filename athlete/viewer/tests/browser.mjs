/** Integration test against the actual GLB, Chrome renderer and Tactics application. */
import { createRequire } from 'node:module'
import fs from 'node:fs'
import path from 'node:path'
import assert from 'node:assert/strict'
const require = createRequire(path.join(process.env.BRAVEN_TACTICS_PATH, 'package.json'))
const puppeteer = require('puppeteer-core')
const output = process.env.BRAVEN_ATHLETE_OUTPUT
const manifest=JSON.parse(fs.readFileSync(path.join(output,'manifest.json'),'utf8'))
fs.mkdirSync(path.join(output, 'verification'), {recursive:true})
const browser = await puppeteer.launch({
  executablePath: process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe',
  headless: true, defaultViewport: {width:1440,height:1000},
})
const page = await browser.newPage()
const downloadDir=fs.mkdtempSync(path.join(output,'verification/pose-'))
const cdp=await page.createCDPSession()
await cdp.send('Page.setDownloadBehavior',{behavior:'allow',downloadPath:downloadDir})
const errors = []
page.on('pageerror', e => errors.push(String(e)))
page.on('console', e => {if(e.type()==='error') errors.push(e.text())})
const report = { checks:[], clips:[], tactics:null, errors }
const input = (selector,value) => page.$eval(selector,(el,value)=>{el.value=value;el.dispatchEvent(new Event('input',{bubbles:true}))},value)
const check = (name,condition) => {assert(condition,name);report.checks.push(name)}
const shot = name => page.screenshot({path:path.join(output,'verification',name+'.png'),fullPage:true})

try {
  await page.goto(process.env.ATHLETE_URL||'http://127.0.0.1:5391/',{waitUntil:'networkidle0'})
  await page.waitForFunction(()=>!!window.athleteStudio,{timeout:30000})
  await page.evaluate(()=>{window.athleteStudio.state.playing=false})
  const info=await page.evaluate(()=>window.athleteStudio.info())
  check('All live joints and exported clips load',info.boneCount===(manifest.deformationControls||69)&&info.clips.length===manifest.animations.length)
  // This reads deformed vertices, not only bone names or animation metadata.
  const vertices=()=>page.evaluate(async()=>{
    const app=window.athleteStudio
    app.sample()
    const root=app.state.driver==='tactics'?app.rig.group:app.model
    const result=[]
    root.traverse(o=>{if(!o.isSkinnedMesh)return;o.skeleton.update();for(let i=0;i<o.geometry.attributes.position.count;i+=173){
      const p=o.getVertexPosition(i,root.position.clone()).applyMatrix4(o.matrixWorld)
      result.push([p.x,p.y,p.z])
    }})
    return result
  })
  const difference=(a,b)=>Math.max(...a.map((p,i)=>Math.hypot(...p.map((v,j)=>v-b[i][j]))))
  for(const clip of info.clips){
    await page.select('#clip',clip.name)
    await input('#timeline',.08);const a=await vertices()
    // Authored techniques can deliberately hold their opening pose until contact.
    let moving=0
    for(const fraction of [.37,.65,.85]){
      await input('#timeline',clip.duration*fraction)
      moving=Math.max(moving,difference(a,await vertices()))
    }
    // Ready is breathing/head movement; the fitted skirt should not inflate this metric.
    const minimumMovement=clip.name==='Ready'?.001:.005
    check(`${clip.name}: actual skinned vertices animate`,moving>minimumMovement)
    await input('#timeline',.08);const repeated=await vertices()
    check(`${clip.name}: scrub is deterministic`,difference(a,repeated)<1e-5)
    report.clips.push({name:clip.name,maxSampledVertexDisplacementM:moving})
    await input('#timeline',clip.duration*.23);await shot(`clip-${clip.name}`)
  }
  await page.select('#clip','Ready')
  await page.click('[data-tab="kit"]');await page.click('[data-kit="shorts"]')
  check('Shorts choice hides the entire multi-material skirt',await page.evaluate(()=>!window.athleteStudio.model.getObjectByName('Kit_Skirt').visible))
  await shot('shorts')
  await page.click('[data-kit="skirt"]')
  check('Skirt returns on the same body',await page.evaluate(()=>window.athleteStudio.model.getObjectByName('Kit_Skirt').visible))
  const skinBefore=await page.evaluate(()=>window.athleteStudio.model.getObjectByName('Athlete_Body').material.color.getHexString())
  await input('#primary','#ad2145')
  const colours=await page.evaluate(()=>{const out={};window.athleteStudio.model.traverse(o=>{if(o.isMesh)for(const m of Array.isArray(o.material)?o.material:[o.material])if(m.color)out[m.name]=m.color.getHexString()});return out})
  check('Kit recolouring preserves skin',colours.Skin===skinBefore&&colours.Kit_Primary==='ad2145')
  await input('#primary','#087e76')
  await page.click('[data-tab="pose"]');await page.select('#bone','lowerarm_l')
  const handBefore=await vertices()
  await input('#rx','35');const handAfter=await vertices()
  check('Manual bone rotation deforms the mesh',difference(handBefore,handAfter)>.02)
  await shot('manual-pose')
  await page.click('#save-pose')
  const posePath=path.join(downloadDir,'braven-athlete-pose.json')
  for(let i=0;i<100&&!fs.existsSync(posePath);i++) await new Promise(r=>setTimeout(r,100))
  check('Edited pose downloads every joint transform',Object.keys(JSON.parse(fs.readFileSync(posePath,'utf8')).bones).length===info.boneCount)
  await page.click('#reset-joint')
  check('Reset joint restores the frozen pose',difference(handBefore,await vertices())<1e-5)
  await(await page.$('#pose-file')).uploadFile(posePath)
  await page.waitForFunction(()=>document.getElementById('pose-message').textContent==='Pose loaded.')
  check('Saved pose restores the same deformed mesh',difference(handAfter,await vertices())<1e-5)
  await page.click('[data-tab="animate"]');await page.select('#driver','tactics')
  await input('#timeline','.1');const ta=await vertices()
  await input('#timeline','.55');const tb=await vertices()
  check('Actual Tactics retarget deforms this asset',difference(ta,tb)>.1)
  await input('#timeline','.1');check('Tactics scrubbing is deterministic',difference(ta,await vertices())<1e-5)
  await page.click('#skeleton');await shot('tactics-skeleton')
  await page.click('#skeleton');await page.select('#driver','clips');await page.select('#clip','Ready')
  await shot('studio-desktop')
  await page.setViewport({width:390,height:844})
  check('Mobile layout has no horizontal overflow',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1))
  await shot('studio-mobile')
  await page.setViewport({width:1440,height:1000})
  for(const name of ['netball-athlete.glb','netball-athlete.blend','athlete-source.blend']) {
    const size=await page.evaluate(async name=>{const r=await fetch('/athlete-assets/'+name,{method:'HEAD'});return r.ok?Number(r.headers.get('content-length')):0},name)
    check(`${name} is downloadable`,size>100000)
  }

  // The complete Tactics board, with its evaluated timeline, not just the studio adapter.
  const tactics=await browser.newPage()
  const loaded=[]
  tactics.on('response',r=>{if(r.url().includes('netball-athlete.glb'))loaded.push({url:r.url(),status:r.status()})})
  tactics.on('pageerror',e=>errors.push('Tactics: '+String(e)))
  await tactics.goto(process.env.TACTICS_URL||'http://127.0.0.1:5392/',{waitUntil:'networkidle0'})
  await tactics.waitForFunction(()=>!!window.__editor)
  await tactics.evaluate(()=>{
    const template=[...document.querySelectorAll('[role="button"]')].find(b=>b.textContent.includes('Netball — centre pass split drive'))
    if(!template) throw new Error('Netball starting play is not visible')
    template.click()
  })
  await tactics.waitForFunction(()=>!document.querySelector('.launch-card'))
  await tactics.evaluate(()=>{const s=window.__editor.getState();s.setView({avatar:'model'});s.setCamera('iso');s.setTime(1.2)})
  await tactics.waitForFunction(async()=>{const{getActiveScene}=await import('/src/engine/sceneRef.ts');const tokens=[...getActiveScene().tokens.values()].filter(t=>t.skinned);return tokens.length===14&&tokens.every(t=>t.skinned.authored)})
  const real=await tactics.evaluate(async()=>{
    const {getActiveScene}=await import('/src/engine/sceneRef.ts')
    const sm=getActiveScene()
    const tokens=[...sm.tokens.values()].filter(t=>t.skinned)
    return {characters:tokens.length,authored:tokens.filter(t=>t.skinned.authored).length,
      allHaveSkirt:tokens.every(t=>t.skinned.group.getObjectByName('Kit_Skirt')),
      previewBallsHidden:tokens.every(t=>t.skinned.group.getObjectByName('Movement_Ball')?.visible===false),
      materialNames:[...new Set(tokens.flatMap(t=>t.skinned.materials.map(m=>m.name)))]}
  })
  check('Full Tactics application loads the generated GLB',loaded.some(r=>r.status===200))
  check('All 14 netball players use the authored rig',real.characters===14&&real.authored===14&&real.allHaveSkirt)
  check('Tactics retains its own ball without 14 duplicated preview balls',real.previewBallsHidden)
  const boardAt=async time=>{
    await tactics.evaluate(time=>window.__editor.getState().setTime(time),time)
    await tactics.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))))
    return tactics.evaluate(async()=>{const{getActiveScene}=await import('/src/engine/sceneRef.ts');return [...getActiveScene().tokens.values()].filter(t=>t.skinned).map(t=>{const bone=t.skinned.bone.hand_l;return bone.getWorldPosition(bone.position.clone()).toArray()})})
  }
  const boardBefore=await boardAt(.1),boardAfter=await boardAt(1.2)
  check('Tactics play timeline moves the loaded athletes',difference(boardBefore,boardAfter)>.1)
  report.tactics={...real,requests:loaded}
  await tactics.screenshot({path:path.join(output,'verification/tactics-board.png')})
  check('No browser JavaScript errors',errors.length===0)
  report.assetSha256=JSON.parse(fs.readFileSync(path.join(output,'manifest.json'),'utf8')).files['netball-athlete.glb'].sha256
  fs.writeFileSync(path.join(output,'browser-verification.json'),JSON.stringify(report,null,2))
  console.log(JSON.stringify(report,null,2))
} finally {await browser.close()}
