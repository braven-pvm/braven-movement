export const STORAGE_KEY='braven-studio.workspace.v1'
export const createWorkspace=assetHash=>({kind:'braven-studio-workspace',schemaVersion:1,assetHash,current:null,saved:[],drafts:{}})
const requireValue=(condition,message)=>{if(!condition)throw new Error(message)}
const finite=(n,min,max)=>Number.isFinite(n)&&n>=min&&n<=max
const vector=(value,length,limit=100)=>Array.isArray(value)&&value.length===length&&value.every(n=>finite(n,-limit,limit))
function validateSetup(setup,catalog) {
  requireValue(setup&&setup.modelId==='netball-athlete'&&setup.assetHash===catalog.assetHash,'This setup belongs to a different model asset.')
  const clip=catalog.animations.find(a=>a.id===setup.clip)
  requireValue(clip,'This setup uses an animation that is not available.')
  requireValue(['clips','tactics'].includes(setup.driver),'Unknown movement source.')
  requireValue(finite(setup.time,0,setup.driver==='tactics'?4:clip.duration+.01),'Invalid animation time.')
  requireValue(['skirt','shorts'].includes(setup.kit),'This kit is not available.')
  requireValue(finite(setup.height,1.60,1.95),'Invalid athlete height.')
  requireValue(finite(setup.speed,.25,2),'Invalid playback speed.')
  requireValue(['run','walk','sprint','static'].includes(setup.gait),'Invalid gait.')
  requireValue(setup.scenario===undefined||['gait','receive-pivot'].includes(setup.scenario),'Invalid Tactics preview.')
  for(const key of ['loop','carry','skeleton','wireframe'])requireValue(typeof setup[key]==='boolean',`Invalid ${key} setting.`)
  for(const key of ['primary','accent','shorts'])requireValue(/^#[0-9a-f]{6}$/i.test(setup.colours?.[key]),'Invalid kit colour.')
  requireValue(vector(setup.camera?.position,3)&&vector(setup.camera?.target,3),'Invalid camera position.')
  if(setup.pose!==null) {
    requireValue(setup.pose&&typeof setup.pose==='object'&&!Array.isArray(setup.pose)&&Object.keys(setup.pose).length<=200,'Invalid saved pose.')
    for(const [name,bone] of Object.entries(setup.pose)) {
      requireValue(/^[a-z0-9_ .-]{1,80}$/i.test(name)&&!['__proto__','constructor','prototype'].includes(name),'Invalid joint name.')
      requireValue(vector(bone.quaternion,4,1)&&Math.abs(Math.hypot(...bone.quaternion)-1)<.01,'Invalid joint rotation.')
      // The original unloaded clips hide their ball with an all-zero scale.
      // Preserve those poses while still refusing collapsed body joints.
      requireValue(vector(bone.position,3,10)&&vector(bone.scale,3,10)&&
        (bone.scale.every(n=>n>0)||(name==='Ball_Control'&&bone.scale.every(n=>n===0))),'Invalid joint transform.')
    }
  }
  // Keep only supported values; imported files do not become arbitrary application state.
  return {modelId:setup.modelId,assetHash:setup.assetHash,clip:setup.clip,time:setup.time,kit:setup.kit,height:setup.height,speed:setup.speed,
    loop:setup.loop,colours:{...setup.colours},driver:setup.driver,gait:setup.gait,...(setup.scenario?{scenario:setup.scenario}:{}),carry:setup.carry,skeleton:setup.skeleton,wireframe:setup.wireframe,
    camera:{position:[...setup.camera.position],target:[...setup.camera.target]},pose:setup.pose===null?null:structuredClone(setup.pose)}
}
export function validateWorkspace(data,catalog) {
  requireValue(data?.kind==='braven-studio-workspace'&&data.schemaVersion===1,'Choose a Braven Studio workspace file (version 1).')
  requireValue(data.assetHash===catalog.assetHash,'This workspace belongs to a different model asset. Load its matching Studio version.')
  requireValue(Array.isArray(data.saved)&&data.saved.length<=50,'A workspace can contain up to 50 saved setups.')
  const ids=new Set()
  const drafts={}
  for(const [clip,note] of Object.entries(data.drafts||{})){
    requireValue(catalog.animations.some(a=>a.id===clip)&&typeof note==='string'&&note.length<=4000,'Invalid draft review note.')
    drafts[clip]=note
  }
  const saved=data.saved.map(entry=>{
    requireValue(typeof entry.id==='string'&&entry.id.length>0&&entry.id.length<=100,'Invalid saved setup identity.')
    requireValue(!ids.has(entry.id),'Duplicate saved setup identity.');ids.add(entry.id)
    requireValue(typeof entry.name==='string'&&entry.name.trim().length>0&&entry.name.length<=80,'Name the setup using 1–80 characters.')
    requireValue(typeof entry.note==='string'&&entry.note.length<=4000,'Review notes must be 4,000 characters or fewer.')
    requireValue(typeof entry.createdAt==='string'&&Number.isFinite(Date.parse(entry.createdAt)),'Invalid saved date.')
    return {id:entry.id,name:entry.name.trim(),note:entry.note,createdAt:entry.createdAt,setup:validateSetup(entry.setup,catalog)}
  })
  return {kind:data.kind,schemaVersion:1,assetHash:data.assetHash,current:data.current?validateSetup(data.current,catalog):null,saved,drafts}
}
export function readWorkspace(storage,catalog) {
  const key=`${STORAGE_KEY}.${catalog.assetHash}`
  let text
  try {
    text=storage.getItem(key)
    return {workspace:text?validateWorkspace(JSON.parse(text),catalog):createWorkspace(catalog.assetHash),error:null}
  } catch(error) {
    let recovered=false
    try{if(text){storage.setItem(`${key}.recovery`,text);recovered=true}}catch{/* Preserve the original key even if browser storage is full. */}
    return {workspace:createWorkspace(catalog.assetHash),error:`Saved workspace could not be read. ${error.message}${recovered?' A recovery copy was kept in browser storage.':' The original data has not been removed.'}`}
  }
}
export function writeWorkspace(storage,workspace,catalog) {
  const valid=validateWorkspace(workspace,catalog)
  try {storage.setItem(`${STORAGE_KEY}.${catalog.assetHash}`,JSON.stringify(valid))}
  catch {throw new Error('Could not save in this browser. Export your workspace to keep a backup.')}
  return valid
}
