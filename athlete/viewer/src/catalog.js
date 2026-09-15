export const clipLabels = {
  Ready:'Ready stance', Jog:'Jog', Defence:'Defensive stance', Receive_pass:'Receive and pass', Jump_reach:'Jump and reach',
  netball_two_hand_catch_chest:'Chest catch', netball_two_hand_snatch_pull_in:'Two-hand snatch, pull in',
  netball_two_hand_snatch_straight_back:'Two-hand snatch, straight back', netball_one_hand_snatch_to_other_hand:'One-hand snatch and transfer',
  netball_hooks_jump_pull_in:'Jump catch and pull in', netball_hooks_outside_hand:'Outside-hand hook catch',
  netball_chest_pass:'Chest pass', netball_overhead_pass:'Overhead pass', netball_bounce_pass:'Bounce pass',
  netball_one_hand_high_pass:'One-hand high pass', netball_deflect_high:'High deflection', netball_double_foot_landing:'Double-foot landing',
}
export const categories = ['All','Passing','Catching','Footwork','Defence']
function category(id) {
  if (/catch|snatch|hooks/.test(id)) return 'Catching'
  if (/pass/i.test(id)) return 'Passing'
  if (/Defence|deflect/.test(id)) return 'Defence'
  return 'Footwork'
}
export function makeCatalog(clips, library, assetHash, revision=6) {
  return {
    assetHash,
    models:[{id:'netball-athlete',name:'Netball athlete',sport:'Netball',description:'Adult female athlete',revision}],
    kits:[{id:'skirt',name:'Skirt and shorts',description:'Fitted skirt with undershorts'},{id:'shorts',name:'Shorts',description:'Sleeveless jersey and court shorts'}],
    animations:clips.map(clip=>{
      const source=library.techniques.find(t=>t.clip===clip.name)
      return {id:clip.name,name:clipLabels[clip.name]||clip.name.replaceAll('_',' '),category:category(clip.name),duration:clip.duration,
        source:source?'Braven Movement':'General movement',review:source?(source.sourceChecksPassed?'Source checked':'Needs review'):'Demonstration',
        coachApproved:source?.coachApproved===true,phases:source?.phases||[]}
    }),
  }
}
export function filterAnimations(animations,query='',category='All') {
  const words=query.toLowerCase().trim().split(/\s+/).filter(Boolean)
  return animations.filter(a=>(category==='All'||a.category===category)&&words.every(word=>`${a.name} ${a.category} ${a.review}`.toLowerCase().includes(word)))
}
