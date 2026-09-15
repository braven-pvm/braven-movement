import test from 'node:test'
import assert from 'node:assert/strict'
import { makeCatalog, filterAnimations } from '../src/catalog.js'
import { STORAGE_KEY, validateWorkspace, createWorkspace, writeWorkspace, readWorkspace } from '../src/workspace.js'

const hash = 'a'.repeat(64)
const catalog = makeCatalog([{name:'netball_chest_pass',duration:1.8},{name:'netball_hooks_jump_pull_in',duration:1.2},{name:'Jog',duration:1}], {
  techniques:[{clip:'netball_chest_pass',sourceChecksPassed:true,coachApproved:false},{clip:'netball_hooks_jump_pull_in',sourceChecksPassed:false,coachApproved:false}],
}, hash)
const setup = () => ({modelId:'netball-athlete',assetHash:hash,clip:'netball_chest_pass',time:0.7,kit:'shorts',height:1.75,speed:1,loop:true,
  colours:{primary:'#087e76',accent:'#ef775e',shorts:'#202b31'},driver:'clips',gait:'run',carry:false,skeleton:false,wireframe:false,
  camera:{position:[0,1.75,4.1],target:[0,0.93,0]},pose:null})

test('catalog uses actual clips and keeps source checks distinct from coaching approval',()=>{
  assert.equal(catalog.models.length,1)
  assert.equal(catalog.animations.length,3)
  assert.equal(catalog.animations[0].review,'Source checked')
  assert.equal(catalog.animations[0].coachApproved,false)
  assert.equal(catalog.animations[1].category,'Catching')
})
test('moving-receive preview persists while older setups keep their gait preview',()=>{
  const state=createWorkspace(hash);state.current={...setup(),driver:'tactics',scenario:'receive-pivot',time:2.2}
  assert.equal(validateWorkspace(state,catalog).current.scenario,'receive-pivot')
  delete state.current.scenario;assert.equal(validateWorkspace(state,catalog).current.scenario,undefined)
  state.current.scenario='unknown';assert.throws(()=>validateWorkspace(state,catalog),/preview/)
})
test('search and category filters combine, including readable technique names',()=>{
  assert.equal(filterAnimations(catalog.animations,'jump','Catching').length,1)
  assert.equal(filterAnimations(catalog.animations,'jump','Passing').length,0)
  assert.equal(filterAnimations(catalog.animations,'CHEST','All')[0].id,'netball_chest_pass')
})
test('workspace roundtrips a named review, notes and exact pose',()=>{
  const state=createWorkspace(hash)
  state.current=setup()
  state.saved=[{id:'review-1',name:'Release check',note:'Look at left wrist',createdAt:'2026-09-14T12:00:00Z',setup:setup()}]
  state.saved[0].setup.pose={hand_l:{quaternion:[0,0,0,1],position:[0,.3,0],scale:[1,1,1]}}
  const roundtrip=validateWorkspace(JSON.parse(JSON.stringify(state)),catalog)
  assert.equal(roundtrip.saved[0].note,'Look at left wrist')
  assert.deepEqual(roundtrip.saved[0].setup.pose.hand_l.quaternion,[0,0,0,1])
})
test('an unloaded pose preserves the hidden ball scale without allowing collapsed body joints',()=>{
  const state=createWorkspace(hash);state.current=setup()
  const transform={quaternion:[0,0,0,1],position:[0,0,0],scale:[0,0,0]}
  state.current.pose={Ball_Control:transform}
  assert.deepEqual(validateWorkspace(state,catalog).current.pose.Ball_Control.scale,[0,0,0])
  state.current.pose={hand_l:transform}
  assert.throws(()=>validateWorkspace(state,catalog),/transform/i)
  state.current.pose={Ball_Control:{...transform,scale:[1,0,1]}}
  assert.throws(()=>validateWorkspace(state,catalog),/transform/i)
})
test('incompatible asset or invalid animation does not silently restore',()=>{
  const state=createWorkspace(hash);state.current=setup()
  assert.throws(()=>validateWorkspace({...state,assetHash:'b'.repeat(64)},catalog),/model|asset/i)
  state.current.clip='unavailable'
  assert.throws(()=>validateWorkspace(state,catalog),/animation/i)
})
test('rejects invalid transforms, unbounded values and unsupported schema before saving',()=>{
  const state=createWorkspace(hash);state.current=setup()
  assert.throws(()=>validateWorkspace({...state,schemaVersion:99},catalog),/version/i)
  state.current.height=Infinity
  assert.throws(()=>validateWorkspace(state,catalog),/height/i)
  state.current=setup();state.current.pose={hand_l:{quaternion:[0,0,0,4],position:[0,0,0],scale:[1,1,1]}}
  assert.throws(()=>validateWorkspace(state,catalog),/rotation/i)
  state.current=setup();state.current.colours.primary='<script>'
  assert.throws(()=>validateWorkspace(state,catalog),/colour/i)
})
test('corrupt storage and quota failures are reported, not called saved',()=>{
  const corrupt={getItem:()=>'{broken',setItem:()=>{throw Error('quota')}}
  const loaded=readWorkspace(corrupt,catalog)
  assert.equal(loaded.workspace.saved.length,0)
  assert.match(loaded.error,/saved|read/i)
  assert.throws(()=>writeWorkspace(corrupt,createWorkspace(hash),catalog),/save|storage/i)
})
test('duplicate review identities are refused instead of deleting the wrong item',()=>{
  const state=createWorkspace(hash)
  const entry={id:'same',name:'Check',note:'',createdAt:'2026-09-14',setup:setup()}
  state.saved=[entry,entry]
  assert.throws(()=>validateWorkspace(state,catalog),/duplicate/i)
})
test('a new model revision does not overwrite the previous model workspace',()=>{
  const values=new Map(),storage={getItem:key=>values.get(key),setItem:(key,value)=>values.set(key,value)}
  const first=createWorkspace(hash);first.current=setup();first.drafts={netball_chest_pass:'Keep this review'}
  writeWorkspace(storage,first,catalog)
  const secondCatalog={...catalog,assetHash:'b'.repeat(64)}
  writeWorkspace(storage,createWorkspace(secondCatalog.assetHash),secondCatalog)
  assert.equal(readWorkspace(storage,catalog).workspace.drafts.netball_chest_pass,'Keep this review')
})
test('unreadable saved data is copied to a recovery key before normal work resumes',()=>{
  const key=`${STORAGE_KEY}.${hash}`,values=new Map([[key,'{broken']])
  const storage={getItem:key=>values.get(key),setItem:(key,value)=>values.set(key,value)}
  const result=readWorkspace(storage,catalog)
  assert.ok(result.error)
  assert.equal(values.get(`${key}.recovery`),'{broken')
  assert.equal(values.get(key),'{broken')
})
