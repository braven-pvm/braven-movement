/** Record the live WebGL athlete, with no pre-rendered image substitution. */
import {createRequire} from 'node:module'
import fs from 'node:fs'
import path from 'node:path'
const require=createRequire(path.join(process.env.BRAVEN_TACTICS_PATH,'package.json'))
const browser=await require('puppeteer-core').launch({
  executablePath:process.env.CHROME_PATH||'C:/Program Files/Google/Chrome/Application/chrome.exe',
  headless:true,defaultViewport:{width:1280,height:940},
})
try {
  const page=await browser.newPage()
  await page.goto(process.env.ATHLETE_URL||'http://127.0.0.1:5391/',{waitUntil:'networkidle0'})
  await page.waitForFunction(()=>window.athleteStudio)
  const bytes=await page.evaluate(async()=>{
    const app=window.athleteStudio
    app.playClip('netball_two_hand_snatch_pull_in');app.state.playing=true;app.state.speed=1
    app.controls.target.set(0,1,.3);app.camera.position.set(2.7,1.9,4.3);app.controls.update()
    const stream=app.renderer.domElement.captureStream(24)
    const recorder=new MediaRecorder(stream,{mimeType:'video/webm;codecs=vp9',videoBitsPerSecond:2000000})
    const chunks=[]
    recorder.ondataavailable=e=>chunks.push(e.data)
    const done=new Promise(resolve=>recorder.onstop=resolve)
    recorder.start()
    for(const clip of ['Jump_reach','netball_hooks_jump_pull_in','netball_double_foot_landing','netball_chest_pass']) {
      app.playClip(clip)
      await new Promise(r=>setTimeout(r,3000))
    }
    recorder.stop();await done;stream.getTracks().forEach(t=>t.stop())
    return Array.from(new Uint8Array(await new Blob(chunks,{type:'video/webm'}).arrayBuffer()))
  })
  const file=path.join(process.env.BRAVEN_ATHLETE_OUTPUT,'athlete-in-motion.webm')
  fs.writeFileSync(file,Buffer.from(bytes))
  console.log(JSON.stringify({file,bytes:bytes.length}))
} finally {await browser.close()}
