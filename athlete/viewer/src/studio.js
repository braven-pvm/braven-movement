import { makeCatalog, filterAnimations, categories } from './catalog.js'
import { createWorkspace, readWorkspace, writeWorkspace, validateWorkspace } from './workspace.js'

const $=id=>document.getElementById(id)
const escape=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))
const symbols={Passing:'↗',Catching:'↓',Footwork:'↟',Defence:'↔'}
const download=(name,data,type='application/json')=>{
  const a=document.createElement('a'),url=URL.createObjectURL(new Blob([data],{type}));a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)
}
function kitArt(kit,colour,accent) {
  return `<svg class="kit-art" aria-hidden="true" viewBox="0 0 220 180"><path d="M85 20 99 28Q110 37 121 28L135 20 146 45 133 53 133 102 87 102 87 53 74 45Z" fill="${colour}"/><path d="M99 28Q110 37 121 28" fill="none" stroke="${accent}" stroke-width="3"/>${kit==='skirt'?`<path d="M87 105 133 105 142 150Q110 158 78 150Z" fill="${colour}"/><path d="M79 148Q110 156 141 148" fill="none" stroke="${accent}" stroke-width="5"/>`:'<path d="M86 105 134 105 139 153 113 153 110 127 107 153 81 153Z" fill="#293e3e"/>'}<text x="110" y="77" text-anchor="middle" fill="white" font-size="16" font-family="Arial">GS</text></svg>`
}
export function startStudio(app) {
  const catalog=makeCatalog(app.clips,app.movementLibrary,app.assetHash,app.assetRevision)
  let storage
  try{storage=window.localStorage}catch{storage={getItem:()=>{throw Error('Browser storage is unavailable.')},setItem:()=>{throw Error('Browser storage is unavailable.')}}}
  let {workspace,error}=readWorkspace(storage,catalog)
  let section='animations',lastClip=app.state.clip,saveTimer,notificationTimer,undo=null,restoring=false,storageWarning=false
  const notify=(message,isError=false,undoAction=null)=>{
    clearTimeout(notificationTimer);$('notification-text').textContent=message;$('notification').hidden=false
    $('notification').classList.toggle('error',isError);undo=undoAction;$('undo-delete').hidden=!undo
    if(!isError&&!undo)notificationTimer=setTimeout(()=>$('notification').hidden=true,5500)
  }
  const current=()=>catalog.animations.find(a=>a.id===app.state.clip)
  const tab=name=>document.querySelector(`[data-tab="${name}"]`).click()
  function persist() {
    if(restoring)return
    try{
      workspace=writeWorkspace(storage,{...workspace,current:app.captureSetup(),drafts:{...workspace.drafts,[app.state.clip]:$('review-note').value}},catalog)
      storageWarning=false
    }catch(e){if(!storageWarning){notify(e.message,true);storageWarning=true}}
  }
  const scheduleSave=()=>{clearTimeout(saveTimer);saveTimer=setTimeout(persist,350)}
  function sync() {
    const item=current()
    if(lastClip!==app.state.clip){
      workspace.drafts[lastClip]=$('review-note').value
      $('review-note').value=workspace.drafts[app.state.clip]||'';lastClip=app.state.clip
    }
    $('stage-title').textContent=app.state.driver==='tactics'?(app.state.scenario==='receive-pivot'?'Moving receive, pivot and pass':`Tactics ${app.state.gait==='static'?'ready stance':app.state.gait}`):item.name
    $('stage-category').textContent=`Netball / ${app.state.driver==='tactics'?'Live movement':item.category}`
    $('stage-subtitle').textContent=`Netball athlete · ${catalog.kits.find(k=>k.id===app.state.kit).name}${app.state.poseMode?' · Edited pose':''}`
    $('playback-rate').textContent=`${app.state.speed}× speed`
    $('review-title').textContent=item.name;$('review-status').textContent=item.review
    $('review-status').classList.toggle('needs-review',item.review==='Needs review')
    $('review-description').textContent=item.source==='General movement'?'An editable demonstration, not a coach-approved technique.':`${item.review==='Source checked'?'Source checkpoints passed.':'Some source checkpoints still need review.'} This retarget has not been coach-approved.`
    $('phase-heading').hidden=app.state.driver!=='clips'||!item.phases.length
    document.querySelectorAll('[data-animation]').forEach(b=>{b.classList.toggle('selected',b.dataset.animation===app.state.clip&&app.state.driver==='clips');b.setAttribute('aria-pressed',String(b.classList.contains('selected')))})
    document.querySelectorAll('[data-library-kit]').forEach(b=>{b.classList.toggle('selected',b.dataset.libraryKit===app.state.kit);b.setAttribute('aria-pressed',String(b.classList.contains('selected')))})
    $('saved-count').textContent=workspace.saved.length
  }
  function chooseAnimation(id) {
    app.selectClip(id)
    tab('animate');sync();scheduleSave()
    if(innerWidth<=700)$('stage').scrollIntoView({block:'start'})
  }
  function render() {
    const descriptions={animations:'Explore movement on your athlete.',kits:'Try a kit. Find the right fit.',models:'The athletes in your library.',saved:'Your setups and review notes.'}
    $('library-title').textContent=section[0].toUpperCase()+section.slice(1);$('library-description').textContent=descriptions[section]
    $('animation-filters').hidden=section!=='animations'
    const host=$('library-results');host.replaceChildren()
    if(section==='animations') {
      const order=['Passing','Catching','Footwork','Defence']
      const items=filterAnimations(catalog.animations,$('library-search').value,$('category').value)
        .sort((a,b)=>order.indexOf(a.category)-order.indexOf(b.category)||a.name.localeCompare(b.name))
      $('library-count').textContent=items.length
      if(!items.length)host.innerHTML='<p class="empty">No matching animations. Try a different search or choose All movements.</p>'
      for(const item of items){
        const button=document.createElement('button');button.className='animation-item';button.dataset.animation=item.id
        button.innerHTML=`<span class="motion-symbol" aria-hidden="true">${symbols[item.category]}</span><span class="item-content"><span class="item-title">${escape(item.name)}</span><span class="item-meta">${escape(item.category)}</span><span class="item-bottom"><span class="status-mark ${item.review==='Needs review'?'review':item.review==='Demonstration'?'demo':''}">${escape(item.review)}</span><span class="item-duration">${item.duration.toFixed(2)} s</span></span></span>`
        button.onclick=()=>chooseAnimation(item.id);host.append(button)
      }
    } else if(section==='kits'){
      $('library-count').textContent=catalog.kits.length
      for(const kit of catalog.kits){
        const button=document.createElement('button');button.className='asset-card';button.dataset.libraryKit=kit.id
        button.innerHTML=`${kitArt(kit.id,$('primary').value,$('accent').value)}<h3>${escape(kit.name)}</h3><p>${escape(kit.description)}</p><span class="asset-tag">Netball</span>`
        button.onclick=()=>{document.querySelector(`[data-kit="${kit.id}"]`).click();tab('kit');sync();scheduleSave();if(innerWidth<=700)$('stage').scrollIntoView()};host.append(button)
      }
    } else if(section==='models'){
      $('library-count').textContent=catalog.models.length
      host.innerHTML='<button class="asset-card selected" id="model-card"><div class="model-art" aria-hidden="true"><svg viewBox="0 0 64 112"><circle cx="32" cy="11" r="10"/><path d="M19 27Q32 21 45 27L53 65 46 67 39 44 39 69 44 108 35 108 32 78 29 108 20 108 25 69 25 44 18 67 11 65Z"/></svg></div><h3>Netball athlete</h3><p>Adult female athlete</p><span class="asset-tag">Revision 6</span></button><p class="hint">70 rig controls. Editable body, fingers and kit. More models will appear here as they are added to the library.</p>'
      $('model-card').querySelector('.asset-tag').textContent=`Revision ${catalog.models[0].revision}`
      $('model-card').onclick=()=>tab('review')
    } else {
      $('library-count').textContent=workspace.saved.length
      if(!workspace.saved.length){host.innerHTML='<div class="saved-empty"><h3>A place to pick up again.</h3><p>Set a pose, choose your kit and add a note. Save the setup to return to it later.</p><button id="save-first">Save your first setup</button></div>';$('save-first').onclick=openSave}
      for(const entry of [...workspace.saved].reverse()){
        const row=document.createElement('article');row.className='saved-item'
        const button=document.createElement('button');button.textContent=entry.name;button.dataset.saved=entry.id
        button.onclick=()=>{
          try{restoring=true;app.applySetup(entry.setup);sync();$('review-note').value=entry.note;workspace.drafts[entry.setup.clip]=entry.note;tab(entry.setup.pose?'pose':'review');notify(`Opened “${entry.name}”.`)}catch(e){notify(e.message,true)}finally{restoring=false;scheduleSave()}
        }
        const description=document.createElement('small');description.textContent=`${catalog.animations.find(a=>a.id===entry.setup.clip).name} · ${entry.setup.time.toFixed(2)} s`
        const note=document.createElement('p');note.textContent=entry.note||'No review note.'
        const remove=document.createElement('button');remove.className='delete-setup';remove.textContent='Remove';remove.setAttribute('aria-label',`Remove ${entry.name}`)
        remove.onclick=()=>{
          try{
            const previous=workspace
            workspace=writeWorkspace(storage,{...workspace,saved:workspace.saved.filter(s=>s.id!==entry.id)},catalog);render()
            notify('Setup removed.',false,()=>{try{workspace=writeWorkspace(storage,{...workspace,saved:previous.saved},catalog);render();notify('Setup restored.')}catch(e){notify(e.message,true)}})
          }catch(e){notify(e.message,true)}
        }
        row.append(button,description,note,remove);host.append(row)
      }
    }
    sync()
  }
  function openSave(){
    $('save-error').hidden=true
    app.pause();$('setup-name').value=`${$('stage-title').textContent}${app.state.poseMode?' pose':''}`;$('setup-note').value=$('review-note').value
    $('save-dialog').showModal();$('setup-name').select();sync()
  }
  for(const name of categories){const option=new Option(name==='All'?'All movements':name,name);if(name==='All')$('category').replaceChildren();$('category').append(option)}
  document.querySelectorAll('[data-section]').forEach(button=>button.onclick=()=>{
    section=button.dataset.section
    document.querySelectorAll('[data-section]').forEach(b=>{b.classList.toggle('selected',b===button);if(b===button)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current')})
    render();if(innerWidth<=700)document.querySelector('.library').scrollIntoView({block:'start'})
  })
  $('library-search').oninput=render;$('category').onchange=render
  $('save-setup').onclick=openSave;$('save-review').onclick=openSave
  $('close-save').onclick=$('cancel-save').onclick=()=>$('save-dialog').close()
  $('save-form').onsubmit=event=>{
    event.preventDefault()
    try{
      const entry={id:crypto.randomUUID(),name:$('setup-name').value.trim(),note:$('setup-note').value,createdAt:new Date().toISOString(),setup:app.captureSetup()}
      workspace=writeWorkspace(storage,{...workspace,current:entry.setup,saved:[...workspace.saved,entry],drafts:{...workspace.drafts,[app.state.clip]:entry.note}},catalog)
      $('review-note').value=entry.note;$('save-dialog').close();render();notify(`Saved “${entry.name}” in this browser.`)
    }catch(e){$('save-error').textContent=e.message;$('save-error').hidden=false}
  }
  $('close-notification').onclick=()=>$('notification').hidden=true
  $('undo-delete').onclick=()=>undo?.()
  $('review-note').oninput=scheduleSave
  $('export-workspace').onclick=()=>{
    try{const output=validateWorkspace({...workspace,current:app.captureSetup(),drafts:{...workspace.drafts,[app.state.clip]:$('review-note').value}},catalog)
      download('braven-studio-workspace.json',JSON.stringify(output,null,2));notify('Workspace exported with saved setups and notes.')
    }catch(e){notify(e.message,true)}
  }
  $('import-workspace').onclick=()=>$('workspace-file').click()
  $('workspace-file').onchange=async()=>{
    const file=$('workspace-file').files[0];if(!file)return
    try{
      if(file.size>5_000_000)throw Error('Choose a workspace file smaller than 5 MB.')
      const imported=validateWorkspace(JSON.parse(await file.text()),catalog)
      const saved=[...workspace.saved]
      for(const entry of imported.saved){
        if(saved.some(s=>JSON.stringify(s)===JSON.stringify(entry)))continue
        saved.push(saved.some(s=>s.id===entry.id)?{...entry,id:crypto.randomUUID()}:entry)
      }
      // Validate the entire candidate before changing the model or stored workspace.
      const candidate=validateWorkspace({...imported,saved,drafts:{...workspace.drafts,...imported.drafts}},catalog)
      for(const setup of [candidate.current,...candidate.saved.map(s=>s.setup)].filter(Boolean))if(setup.pose)for(const name of Object.keys(setup.pose))if(!app.bones.has(name))throw Error(`Unknown joint: ${name}`)
      workspace=writeWorkspace(storage,candidate,catalog)
      restoring=true;if(workspace.current)app.applySetup(workspace.current);sync();$('review-note').value=workspace.drafts[app.state.clip]||'';restoring=false
      render();notify('Workspace imported. Existing saved setups were kept.')
    }catch(e){restoring=false;notify(`Could not import workspace. ${e.message}`,true)}finally{$('workspace-file').value=''}
  }
  $('reset-colours').onclick=()=>{
    for(const [id,value] of Object.entries({primary:'#087e76',accent:'#ef775e',shorts:'#202b31'}))$(id).value=value
    app.appearance();if(section==='kits')render();scheduleSave()
  }
  $('capture-frame').onclick=()=>{
    app.sample();app.renderer.render(app.scene,app.camera)
    const label=app.state.driver==='tactics'&&app.state.scenario==='receive-pivot'?'moving-receive-pivot':app.state.clip
    const a=document.createElement('a');a.href=app.renderer.domElement.toDataURL('image/png');a.download=`braven-${label}-${app.state.time.toFixed(2)}s.png`;a.click();notify('Preview image downloaded.')
  }
  $('restart').onclick=()=>{app.seek(0);sync();scheduleSave()}
  const step=direction=>{app.pause();app.seek(app.state.time+direction/60);sync();scheduleSave()}
  $('step-back').onclick=()=>step(-1);$('step-forward').onclick=()=>step(1)
  document.addEventListener('keydown',event=>{
    if(event.target.closest('input,select,textarea,button,a,[contenteditable="true"]')||$('save-dialog').open)return
    if(event.code==='Space'){event.preventDefault();$('play').click()}
    if(event.code==='ArrowLeft'||event.code==='ArrowRight'){event.preventDefault();step(event.code==='ArrowLeft'?-1:1)}
  })
  // Existing renderer controls own their behavior; observe after those handlers run.
  for(const event of ['input','change','click'])document.addEventListener(event,e=>{
    if(e.target.closest('.inspector,.stage')){sync();scheduleSave()}
  })
  app.controls.addEventListener('end',scheduleSave)
  window.addEventListener('pagehide',persist)
  document.addEventListener('visibilitychange',()=>{if(document.hidden)persist()})
  setInterval(()=>{if(app.state.playing&&!document.hidden)persist()},5000)
  $('library-summary').textContent=`${catalog.models.length} model · ${catalog.kits.length} kits · ${catalog.animations.length} animations`
  $('asset-details').innerHTML=`<dt>Model</dt><dd>Netball athlete, revision ${catalog.models[0].revision}</dd><dt>Rig</dt><dd>${app.bones.size} controls</dd><dt>Motion source</dt><dd>${escape(app.movementLibrary.sourceCommit||'See download manifest')}</dd><dt>Model fingerprint</dt><dd>${escape(app.assetHash)}</dd>`
  if(workspace.current){try{restoring=true;app.applySetup(workspace.current)}catch(e){error=e.message}finally{restoring=false}}
  lastClip=app.state.clip;$('review-note').value=workspace.drafts[app.state.clip]||''
  for(const id of ['save-setup','capture-frame','restart','step-back','step-forward'])$(id).disabled=false
  render();if(error)notify(error,true)
  window.bravenStudio={catalog,get workspace(){return structuredClone(workspace)},get section(){return section}}
}
