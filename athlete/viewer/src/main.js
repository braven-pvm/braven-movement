import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js'
import { buildSkinned, applySkinnedPose, kitColours } from '@tactics/engine/skinned.ts'
import { pose as tacticsPose } from '@tactics/engine/pose.ts'
import { applyAthleteMotion } from '@tactics/engine/athleteMotion.ts'
import { applyAthleteFootwork, prepareAthleteLocomotion } from '@tactics/engine/athleteFootwork.ts'
import { createAthleteFootworkDemo } from '@tactics/state/athleteFootworkDemo.ts'
import { evaluateFrame, distanceAt, paceIn } from '@tactics/core/evaluate.ts'
import { clipLabels } from './catalog.js'
import { startStudio } from './studio.js'
import { receivePassSequence, presentCarryBall, previewPace } from './preview-motion.js'
import './style.css'

const $ = id => document.getElementById(id)
const state = { playing: false, speed: 1, time: 0,
  driver: 'clips', clip: 'Ready', kit: 'skirt', height: 1.75, skeleton: false, wireframe: false,
  gait: 'run', scenario: 'gait', carry: false, poseMode: false, selectedBone: 'upperarm_l', loop: true }
const footworkDemo=createAthleteFootworkDemo()
const host = $('viewport')
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true })
renderer.setPixelRatio(Math.min(devicePixelRatio, 2))
renderer.shadowMap.enabled = true
renderer.shadowMap.type = THREE.PCFSoftShadowMap
renderer.toneMapping = THREE.ACESFilmicToneMapping
renderer.toneMappingExposure = 1.0
host.append(renderer.domElement)
const scene = new THREE.Scene()
scene.background = new THREE.Color('#e8eeea')
scene.fog = new THREE.Fog('#e8eeea', 8, 22)
const pmrem = new THREE.PMREMGenerator(renderer)
const room = new RoomEnvironment()
const environment = pmrem.fromScene(room, .04)
scene.environment = environment.texture
scene.environmentIntensity = .48
room.dispose(); pmrem.dispose()
scene.add(new THREE.HemisphereLight('#e8f4ed', '#4b5d53', 1.2))
const light = new THREE.DirectionalLight('#fff5e8', 3)
light.position.set(3, 6, 4); light.castShadow = true
light.shadow.mapSize.set(2048, 2048)
Object.assign(light.shadow.camera, { left: -3, right: 3, top: 3, bottom: -3, near: .1, far: 15 })
light.shadow.normalBias = .015
scene.add(light)
const fill = new THREE.DirectionalLight('#d2e9e8', 1.1)
fill.position.set(-4, 3, -3); scene.add(fill)
const ground = new THREE.Mesh(new THREE.PlaneGeometry(200, 200), new THREE.MeshStandardMaterial({ color: '#e0e8e1', roughness: 1 }))
ground.rotation.x = -Math.PI/2; ground.position.y = -.015; ground.receiveShadow = true; scene.add(ground)
// A restrained court marking grounds the athlete in sport rather than a model turntable.
const ring = new THREE.Mesh(new THREE.RingGeometry(1.00, 1.007, 128), new THREE.MeshBasicMaterial({ color: '#a1b6a9', transparent: true, opacity: .45, side: THREE.DoubleSide }))
ring.rotation.x = -Math.PI/2; ring.position.y = -.012; scene.add(ring)
const camera = new THREE.PerspectiveCamera(34, 1, .01, 80)
const controls = new OrbitControls(camera, renderer.domElement)
controls.target.set(0, .93, 0)
controls.enableDamping = true; controls.minDistance = 1.2; controls.maxDistance = 7
controls.maxPolarAngle = Math.PI*.52
function view(name) {
  const positions = { front: [0, 1.75, 4.1], side: [4.1, 1.75, 0], back: [0,1.75,-4.1], quarter: [2.2, 1.8, 3.55] }
  camera.position.set(...positions[name]); controls.target.set(0, .93, 0)
  if (state.driver === 'clips' && state.clip === 'Jump_reach') {
    controls.target.y = 1.12
    camera.position.sub(controls.target).multiplyScalar(1.18).add(controls.target)
  }
  if(state.driver==='clips'&&state.clip==='netball_bounce_pass'&&name==='quarter'){
    camera.position.set(5,2.5,6);controls.target.set(0,.8,1.3)
  }
  controls.update()
  const ids={front:'front',side:'side',back:'back',quarter:'three-quarter'}
  for(const id of Object.values(ids)) $(id).classList.toggle('selected',id===ids[name])
}
view('quarter')
new ResizeObserver(() => { camera.aspect = host.clientWidth/host.clientHeight; camera.updateProjectionMatrix(); renderer.setSize(host.clientWidth, host.clientHeight) }).observe(host)

let model, mixer, clips, activeAction, rig, tacticRoot, helper, tacticHelper, originalHeight
let movementLibrary = {techniques: []}
const technique = () => movementLibrary.techniques.find(t => t.clip === state.clip)
const bones = new Map(), bind = new Map(), poseBasis = new Map(), offsets = new Map()
const capture = b => ({ q: b.quaternion.clone(), p: b.position.clone(), s: b.scale.clone() })
const restore = (b, v) => { b.quaternion.copy(v.q); b.position.copy(v.p); b.scale.copy(v.s) }

function appearance() {
  for (const root of [model, tacticRoot].filter(Boolean)) root.traverse(o => {
    if (o.userData.bravenRole === 'skirt') o.visible = state.kit === 'skirt'
    if (!o.isMesh) return
    for (const mat of Array.isArray(o.material) ? o.material : [o.material]) {
      if (!mat.color) continue
      if (mat.name === 'Kit_Primary') mat.color.set($('primary').value)
      if (mat.name === 'Kit_Accent') mat.color.set($('accent').value)
      if (mat.name === 'Kit_Shorts') mat.color.set($('shorts').value)
      mat.wireframe = state.wireframe
    }
  })
  if (model) model.scale.setScalar(state.height/originalHeight)
  if (tacticRoot) tacticRoot.scale.setScalar(state.height/1.75)
  $('height-value').textContent = `${state.height.toFixed(2)} m`
}
function updateVisibility() {
  const tactics = state.driver === 'tactics' && !state.poseMode
  model.visible = !tactics; tacticRoot.visible = tactics
  helper.visible = state.skeleton && !tactics; tacticHelper.visible = state.skeleton && tactics
  $('tactics-options').hidden = !tactics
  $('clip').disabled = tactics
  $('motion-note').hidden = tactics
  const ball = model.getObjectByName('Movement_Ball')
  if (ball) ball.visible = !tactics && (!!technique() || state.clip === 'Receive_pass')
  $('phase-buttons').hidden = tactics || !technique()
  $('status').textContent = tactics ? 'Connected · Braven Tactics pose engine' : state.poseMode ? 'Pose editing · animation paused' : 'Editable source + portable GLB'
}
function playClip(name) {
  previous = performance.now()
  const framing=clip=>['Jump_reach','netball_bounce_pass'].includes(clip)?clip:'default'
  const reframe = framing(name) !== framing(state.clip)
  state.clip = name; state.time = 0; state.poseMode = false
  $('clip').value = name
  if (reframe) view('quarter')
  offsets.clear()
  mixer.stopAllAction()
  activeAction = mixer.clipAction(clips.find(c => c.name === name))
  activeAction.setLoop(THREE.LoopOnce, 1)
  activeAction.clampWhenFinished = true
  activeAction.reset().play()
  mixer.setTime(0)
  const source = technique()
  $('phase-buttons').replaceChildren()
  if (source) {
    for (const phase of source.phases) {
      const button = document.createElement('button')
      button.textContent = phase.name.replaceAll('_', ' ')
      button.dataset.time = phase.time
      button.onclick = () => { if (state.poseMode) playClip(state.clip); state.playing=false; state.time=phase.time; sample() }
      $('phase-buttons').append(button)
    }
    $('motion-note').textContent = `Braven Movement technique. ${source.sourceChecksPassed ? 'Source checkpoints passed.' : 'Source checks need review.'} Retargeted onto this athlete; coaching approval is still pending.`
  } else $('motion-note').textContent = state.clip === 'Receive_pass'
    ? 'Demonstration sequence: Movement two-hand catch into chest pass, including the ball. Coaching approval is pending.'
    : 'Unloaded movement demonstration. Pause at any moment, then open Pose to adjust the body.'
  updateVisibility()
}
// Explicit user selection starts playback; internal sampling and saved setups
// still use playClip so restoring a review never starts moving its pose.
function selectClip(name) {
  state.driver='clips';$('driver').value='clips'
  playClip(name);state.playing=true;sample()
}
function duration() { return state.driver === 'tactics' ? 4 : activeAction?.getClip().duration || 3 }
function sample() {
  if (!model) return
  $('gait-controls').hidden=state.scenario==='receive-pivot'
  if (!state.poseMode) {
    if (state.driver === 'tactics') {
      if(state.scenario==='receive-pivot'){
        const {project,actorId}=footworkDemo,frame=evaluateFrame(project,state.time),actor=frame.actors[actorId],track=project.timeline.tracks[actorId]
        tacticRoot.rotation.y=actor.facing-Math.PI/2
        tacticRoot.position.set(actor.pos.y,0,actor.pos.x).multiplyScalar(state.height/1.75)
        const p=tacticsPose({gait:actor.gait,distance:distanceAt(track.keys,state.time,paceIn(project),track.runs),hasBall:actor.hasBall,height:1.75,build:'feminine'})
        applySkinnedPose(rig,p);prepareAthleteLocomotion(rig,actor.athleteFootwork,actor);if(actor.athleteMotion)applyAthleteMotion(rig,actor.athleteMotion)
        applyAthleteFootwork(rig,actor.athleteFootwork,actor)
        const control=rig.bone.Ball_Control,ball=rig.group.getObjectByName('Movement_Ball')
        const world=new THREE.Vector3(frame.ball.pos.y,frame.ball.elevation-.02,frame.ball.pos.x).multiplyScalar(state.height/1.75)
        control.parent.updateWorldMatrix(true,false);control.position.copy(control.parent.worldToLocal(world));control.scale.set(1,1,1);ball.visible=true
        $('gait-note').textContent='An actual Tactics play: move into the catch, settle, pivot and pass.'
      }else{
      tacticRoot.rotation.y=-Math.PI/2;tacticRoot.position.set(0,0,0)
      const p = tacticsPose({ gait: state.gait, distance: state.time*previewPace[state.gait],
        hasBall: state.carry, height: 1.75, build: 'feminine' })
      applySkinnedPose(rig, p)
      presentCarryBall(rig,state.carry)
      $('gait-note').textContent=`Preview pace: ${(previewPace[state.gait]*state.height/1.75).toFixed(1)} m/s at 1× playback.`
      }
    } else {
      activeAction.enabled = true; activeAction.paused = false
      mixer.setTime(state.time)
    }
  }
  scene.updateMatrixWorld(true)
  let ballSource=technique(),ballTime=state.time
  if(state.clip==='Receive_pass'){
    const passStart=duration()-clips.find(c=>c.name==='netball_chest_pass').duration
    ballSource=movementLibrary.techniques.find(t=>t.clip===(state.time<passStart?'netball_two_hand_snatch_pull_in':'netball_chest_pass'))
    if(state.time>=passStart)ballTime-=passStart
  }
  const dynamics=ballSource?.ballDynamics
  $('ball-phase').hidden=!dynamics||state.driver==='tactics'||state.poseMode
  if(dynamics){
    const outgoing=dynamics.outgoing
    $('ball-phase').textContent=outgoing&&ballTime>=outgoing.start
      ? outgoing.bounceSeconds&&ballTime>=outgoing.bounceSeconds?'Ball rebounding':'Ball released'
      : ballTime>=dynamics.contactSeconds?'Ball controlled'
      : dynamics.incomingStartSeconds!==null&&ballTime>=dynamics.incomingStartSeconds?'Incoming ball':'Waiting for the pass'
  }
  helper.updateMatrixWorld(true); tacticHelper.updateMatrixWorld(true)
  $('timeline').max = duration(); $('timeline').value = state.time
  $('time').textContent = `${state.time.toFixed(2)} / ${duration().toFixed(2)} s`
  $('play').textContent = state.playing ? 'Pause' : 'Play'
}
function enterPose() {
  advancePlayback(performance.now()); sample()
  state.playing = false
  if (state.poseMode) return
  const wasTactics=state.driver==='tactics'
  state.driver = 'clips'; $('driver').value = 'clips'
  // A gait cycle can outlast the selected native clip. Capture a valid native
  // phase and its actual bones together when switching back to pose editing.
  if(wasTactics){state.time=Math.min(state.time,duration()-.001);sample()}
  poseBasis.clear(); offsets.clear()
  for (const [name, bone] of bones) poseBasis.set(name, capture(bone))
  mixer.stopAllAction()
  for (const [name, bone] of bones) restore(bone, poseBasis.get(name))
  state.poseMode = true; updateVisibility(); refreshJoint(); sample()
}
function refreshJoint() {
  const v = offsets.get(state.selectedBone) || [0,0,0,0,0,0]
  for (const [i, id] of ['rx','ry','rz','px','py','pz'].entries()) {
    $(id).value = v[i]
    if (i < 3) $(`${id}-value`).textContent = `${v[i]}°`
  }
}
function applyJoint() {
  enterPose()
  const v = ['rx','ry','rz','px','py','pz'].map(id => Number($(id).value))
  if (!v.every(Number.isFinite)) return
  offsets.set(state.selectedBone, v)
  const bone = bones.get(state.selectedBone), base = poseBasis.get(state.selectedBone)
  restore(bone, base)
  bone.quaternion.multiply(new THREE.Quaternion().setFromEuler(new THREE.Euler(...v.slice(0,3).map(THREE.MathUtils.degToRad))))
  bone.position.add(new THREE.Vector3(...v.slice(3)))
  refreshJoint(); sample()
}
function download(name, data) {
  const url = URL.createObjectURL(new Blob([data], { type: 'application/json' }))
  const a = document.createElement('a'); a.href = url; a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000)
}

async function init() {
  const manifestResponse=await fetch('/athlete-assets/manifest.json')
  if(!manifestResponse.ok)throw new Error('The model manifest is missing. Rebuild Studio with the athlete output directory.')
  const manifest=await manifestResponse.json()
  movementLibrary = await fetch('/athlete-assets/movement-library.json').then(r => r.ok ? r.json() : {techniques:[]}).catch(() => ({techniques:[]}))
  const gltf = await new GLTFLoader().loadAsync('/athlete-assets/netball-athlete.glb', e => {
    $('load-message').textContent = e.total ? `Loading athlete · ${Math.round(e.loaded/e.total*100)}%` : 'Loading athlete…'
  })
  model = gltf.scene
  model.traverse(o => {
    if (o.isBone) { bones.set(o.name, o); bind.set(o.name, capture(o)) }
    if (o.isMesh) { o.castShadow = true; o.frustumCulled = false }
  })
  const bounds = new THREE.Box3().setFromObject(model)
  originalHeight = bounds.max.y-bounds.min.y
  model.position.y = -bounds.min.y
  scene.add(model)
  helper = new THREE.SkeletonHelper(model)
  helper.material.depthTest = false; helper.material.transparent = true; helper.material.opacity = .9
  helper.renderOrder = 5; scene.add(helper)
  const sequence=receivePassSequence(gltf.animations)
  clips = gltf.animations.map(c=>c.name===sequence.name?sequence:c); mixer = new THREE.AnimationMixer(model)
  $('clip').replaceChildren()
  for (const [label, options] of [
    ['Braven Movement', movementLibrary.techniques.filter(t => t.sourceChecksPassed).map(t => t.clip)],
    ['Braven Movement · needs review', movementLibrary.techniques.filter(t => !t.sourceChecksPassed).map(t => t.clip)],
    ['General movement', clips.filter(c => !movementLibrary.techniques.some(t => t.clip===c.name)).map(c => c.name)]]) {
    if (!options.length) continue
    const group = document.createElement('optgroup'); group.label = label
    for (const name of options) group.append(new Option(clipLabels[name] || name, name))
    $('clip').append(group)
  }
  rig = buildSkinned({ gltf, height: 1.75, kit: 'skirt', build: 'feminine',
    colours: kitColours(new THREE.Color('#087e76')) })
  if (!rig.authored) throw new Error('Tactics checkout needs the authored-athlete adapter; see athlete/README.md.')
  tacticRoot = new THREE.Group(); tacticRoot.rotation.y = -Math.PI/2; tacticRoot.add(rig.group); scene.add(tacticRoot)
  tacticHelper = new THREE.SkeletonHelper(rig.group); tacticHelper.material.depthTest = false; tacticHelper.renderOrder = 5; scene.add(tacticHelper)
  const labels = { pelvis:'Pelvis',spine_01:'Lower spine',spine_02:'Mid spine',spine_03:'Chest',neck_01:'Neck',Head:'Head',
    upperarm_l:'Left upper arm', lowerarm_l:'Left elbow', hand_l:'Left wrist', upperarm_r:'Right upper arm', lowerarm_r:'Right elbow', hand_r:'Right wrist',
    thigh_l:'Left hip',calf_l:'Left knee',foot_l:'Left ankle',thigh_r:'Right hip',calf_r:'Right knee',foot_r:'Right ankle',Ball_Control:'Ball position' }
  for (const name of [...Object.keys(labels), ...bones.keys()].filter((v,i,a) => a.indexOf(v)===i && bones.has(v))) {
    const option = new Option(labels[name] || name.replaceAll('_',' '), name); $('bone').add(option)
  }
  $('bone').value = state.selectedBone
  $('model-stats').textContent = `${bones.size} controls · ${clips.length} animations · editable kit`
  $('load-message').hidden = true; $('play').disabled = false; $('timeline').disabled = false
  appearance(); playClip('netball_chest_pass'); sample()
  window.athleteStudio = { state, model, rig, bones, clips, mixer, scene, renderer, camera, controls,
    sample, playClip, selectClip, enterPose, appearance, updateVisibility, movementLibrary, view, duration,
    assetHash:manifest.files['netball-athlete.glb'].sha256.toLowerCase(),
    assetRevision:manifest.revision,
    pause:()=>{advancePlayback(performance.now());state.playing=false;sample()},
    seek:time=>{if(state.poseMode)playClip(state.clip);previous=performance.now();state.playing=false;state.time=Math.max(0,Math.min(time,duration()-.001));sample()},
    captureSetup, applySetup,
    info: () => ({ ...state, boneCount: bones.size, clips: clips.map(c => ({ name:c.name,duration:c.duration })),
      actualTacticsAdapter: rig.authored, renderedFrames: renderer.info.render.frame }),
  }
  startStudio(window.athleteStudio)
}

function captureSetup() {
  return {modelId:'netball-athlete',assetHash:window.athleteStudio.assetHash,clip:state.clip,time:state.time,kit:state.kit,height:state.height,
    speed:state.speed,loop:state.loop,driver:state.driver,gait:state.gait,scenario:state.scenario,carry:state.carry,skeleton:state.skeleton,wireframe:state.wireframe,
    colours:Object.fromEntries(['primary','accent','shorts'].map(id=>[id,$(id).value])),
    camera:{position:camera.position.toArray(),target:controls.target.toArray()},
    pose:state.poseMode?Object.fromEntries([...bones].map(([name,b])=>[name,{quaternion:b.quaternion.toArray(),position:b.position.toArray(),scale:b.scale.toArray()}])):null}
}
function applySetup(setup) {
  if(setup.pose)for(const name of Object.keys(setup.pose))if(!bones.has(name))throw new Error(`The saved pose contains an unavailable joint: ${name}`)
  state.playing=false
  state.scenario=setup.scenario||'gait';$('scenario').value=state.scenario
  for(const key of ['driver','gait','carry','kit','height','speed','loop','skeleton','wireframe'])state[key]=setup[key]
  playClip(setup.clip);state.time=setup.time
  for(const key of ['driver','gait','height','speed'])$(key).value=state[key]
  for(const key of ['carry','loop','skeleton','wireframe'])$(key).checked=state[key]
  for(const key of ['primary','accent','shorts'])$(key).value=setup.colours[key]
  $('speed-value').textContent=`${state.speed}×`
  document.querySelectorAll('[data-kit]').forEach(b=>b.classList.toggle('selected',b.dataset.kit===state.kit))
  appearance();updateVisibility();sample()
  if(setup.pose){
    enterPose();offsets.clear()
    for(const [name,v] of Object.entries(setup.pose)){
      const b=bones.get(name);b.quaternion.fromArray(v.quaternion);b.position.fromArray(v.position);b.scale.fromArray(v.scale);poseBasis.set(name,capture(b))
    }
    refreshJoint();sample()
  }
  camera.position.fromArray(setup.camera.position);controls.target.fromArray(setup.camera.target);controls.update()
  document.querySelectorAll('.view-tools button').forEach(b=>b.classList.remove('selected'))
  previous=performance.now()
}

$('play').onclick = () => {
  advancePlayback(performance.now())
  if (state.poseMode) playClip(state.clip)
  if (state.time >= duration() - .002) state.time = 0
  state.playing = !state.playing; sample()
}
$('timeline').oninput = () => {
  if (state.poseMode) playClip(state.clip)
  previous = performance.now()
  state.playing = false; state.time = Number($('timeline').value); sample()
}
$('clip').onchange = () => selectClip($('clip').value)
$('speed').oninput = () => { advancePlayback(performance.now()); state.speed = Number($('speed').value); $('speed-value').textContent = `${state.speed}×` }
$('driver').onchange = () => { state.driver = $('driver').value; state.poseMode = false; state.time=0; playClip(state.clip); updateVisibility(); sample() }
$('gait').onchange = () => {
  previous=performance.now();state.gait=$('gait').value;state.time=0;state.playing=true;sample()
}
$('scenario').onchange=()=>{state.scenario=$('scenario').value;state.time=0;state.playing=true;previous=performance.now();if(state.scenario==='receive-pivot')view('quarter');sample()}
$('carry').onchange = () => { state.carry = $('carry').checked; sample() }
$('loop').onchange = () => { state.loop = $('loop').checked }
$('skeleton').onchange = () => { state.skeleton = $('skeleton').checked; updateVisibility() }
$('wireframe').onchange = () => { state.wireframe = $('wireframe').checked; appearance() }
for (const id of ['primary','accent','shorts']) $(id).oninput = appearance
$('height').oninput = () => { state.height = Number($('height').value); appearance() }
document.querySelectorAll('[data-kit]').forEach(button => button.onclick = () => {
  state.kit = button.dataset.kit
  document.querySelectorAll('[data-kit]').forEach(b => b.classList.toggle('selected', b === button))
  appearance()
})
document.querySelectorAll('[data-tab]').forEach(button => button.onclick = () => {
  document.querySelectorAll('[data-tab]').forEach(b => { b.classList.toggle('selected', b===button); b.setAttribute('aria-selected', b===button) })
  for (const name of ['animate','kit','review','pose']) $(`panel-${name}`).hidden = name !== button.dataset.tab
  if (button.dataset.tab === 'pose') enterPose()
})
$('bone').onchange = () => { state.selectedBone = $('bone').value; refreshJoint() }
for (const id of ['rx','ry','rz','px','py','pz']) $(id).oninput = applyJoint
$('reset-joint').onclick = () => { offsets.delete(state.selectedBone); refreshJoint(); applyJoint() }
$('reset-pose').onclick = () => { enterPose(); offsets.clear(); for (const [name, bone] of bones) { restore(bone,bind.get(name)); poseBasis.set(name,capture(bone)) } refreshJoint(); sample() }
$('save-pose').onclick = () => {
  enterPose()
  download('braven-athlete-pose.json', JSON.stringify({ schemaVersion:1,kind:'braven-athlete-pose',
    clip: state.clip,
    bones: Object.fromEntries([...bones].map(([name,b]) => [name,{quaternion:b.quaternion.toArray(),position:b.position.toArray(),scale:b.scale.toArray()}])) }, null,2))
  $('pose-message').textContent = 'Pose saved. Load it here to continue editing.'
}
$('load-pose').onclick = () => $('pose-file').click()
$('pose-file').onchange = async () => {
  try {
    const data=JSON.parse(await $('pose-file').files[0].text())
    if(data.kind!=='braven-athlete-pose'||data.schemaVersion!==1||!data.bones) throw new Error('Choose a Braven athlete pose file.')
    for(const [name,v] of Object.entries(data.bones)) {
      if(!bones.has(name)||!Array.isArray(v.quaternion)||v.quaternion.length!==4||!Array.isArray(v.position)||v.position.length!==3||![...v.quaternion,...v.position].every(Number.isFinite)) throw new Error('The pose contains an invalid joint transform.')
      if(Math.abs(Math.hypot(...v.quaternion)-1)>.01) throw new Error('The pose contains an invalid rotation.')
      if(v.scale && (!Array.isArray(v.scale)||v.scale.length!==3||!v.scale.every(Number.isFinite))) throw new Error('The pose contains an invalid scale.')
    }
    if (data.clip && clips.some(c => c.name === data.clip)) playClip(data.clip)
    enterPose(); offsets.clear()
    for(const [name,v] of Object.entries(data.bones)) { const b=bones.get(name);b.quaternion.fromArray(v.quaternion);b.position.fromArray(v.position);if(v.scale)b.scale.fromArray(v.scale);poseBasis.set(name,capture(b)) }
    refreshJoint();sample();$('pose-message').textContent='Pose loaded.'
  } catch(error){$('pose-message').textContent=error.message}
  $('pose-file').value=''
}
$('front').onclick=()=>view('front');$('side').onclick=()=>view('side');$('back').onclick=()=>view('back');$('three-quarter').onclick=()=>view('quarter');$('reset-camera').onclick=()=>view('quarter')

let previous=performance.now()
function advancePlayback(now) {
  // Slow rendering must drop visual frames, not elapsed animation time.
  // Input events can arrive after this frame's rAF timestamp, so never rewind
  // the clock when synchronising a pause or playback-speed change.
  const delta = Math.max(0, (now - previous) / 1000)
  previous = Math.max(previous, now)
  if (!model || document.hidden || !state.playing || state.poseMode) return
  const next = state.time + delta * state.speed
  if (state.loop) state.time = next % duration()
  else {
    state.time = Math.min(next, duration() - .001)
    if (next >= duration() - .001) state.playing = false
  }
}
// A suspended/background preview resumes from its current pose, without
// including the time spent away. Ordinary slow frames retain their full time.
document.addEventListener('visibilitychange', () => { previous = performance.now() })
function animate(now) {
  requestAnimationFrame(animate)
  advancePlayback(now)
  if (model) sample()
  controls.update()
  renderer.render(scene, camera)
}
requestAnimationFrame(animate)
init().catch(error=>{$('load-message').hidden=false;$('load-message').classList.add('error');$('load-message').textContent=`Athlete could not load: ${error.message}`;console.error(error)})
