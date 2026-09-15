import * as THREE from 'three'

// Preview presets for the 1.75 m adapter, using the current Tactics stride
// lengths (0.85 / 1.5 / 1.9 × height). Four, six and eight full strides in the
// four-second preview keep the loop continuous and the gaits in cadence order.
// These are showcase paces, not a measured athlete performance profile.
export const previewPace={static:0,walk:1.4875,run:3.9375,sprint:6.65}

/** Join existing solved movements, including their ball tracks. The downloadable
 * revision 6 asset is unchanged; this editable Studio sequence replaces its old
 * Receive_pass arm-reach demo without inventing a second throw/catch solver. */
export function receivePassSequence(clips) {
  const old=clips.find(c=>c.name==='Receive_pass')
  const receive=clips.find(c=>c.name==='netball_two_hand_snatch_pull_in')
  const pass=clips.find(c=>c.name==='netball_chest_pass')
  if(!old||!receive||!pass)throw Error('Receive and pass needs both Movement source clips.')
  const start=old.duration-pass.duration,overlap=receive.duration-start
  if(overlap<=0)throw Error('Receive/pass sources do not overlap within the demonstration duration.')
  const right=new Map(pass.tracks.map(t=>[t.name,t])),frames=Math.ceil(old.duration*60)
  const times=Array.from({length:frames+1},(_,i)=>Math.min(i/60,old.duration))
  const tracks=receive.tracks.map(left=>{
    const next=right.get(left.name)
    if(!next||left.ValueTypeName!==next.ValueTypeName)throw Error(`Receive/pass track mismatch: ${left.name}`)
    const a=left.createInterpolant(),b=next.createInterpolant(),values=[],qa=new THREE.Quaternion(),qb=new THREE.Quaternion()
    for(const time of times){
      const av=a.evaluate(Math.min(time,receive.duration)),bv=b.evaluate(Math.max(0,time-start))
      const blend=THREE.MathUtils.clamp((time-start)/overlap,0,1)
      if(left.ValueTypeName==='quaternion')values.push(...qa.fromArray(av).slerp(qb.fromArray(bv),blend).toArray())
      else for(let i=0;i<av.length;i++)values.push(THREE.MathUtils.lerp(av[i],bv[i],blend))
    }
    return new left.constructor(left.name,times,values)
  })
  if(tracks.length!==pass.tracks.length)throw Error('Receive/pass sources have different rig tracks.')
  return new THREE.AnimationClip(old.name,old.duration,tracks)
}

function rotateToward(bone,from,to) {
  const rotation=new THREE.Quaternion().setFromUnitVectors(from.normalize(),to.normalize())
  const world=bone.getWorldQuaternion(new THREE.Quaternion()).premultiply(rotation)
  bone.quaternion.copy(bone.parent.getWorldQuaternion(new THREE.Quaternion()).invert().multiply(world))
  bone.updateWorldMatrix(false,true)
}

/** Two-link arm solve from the actual skin's segment lengths. Keep the current
 * elbow plane and wrist orientation; bring each palm onto the held ball without
 * stretching bones. Called after the Tactics pose resets the authored skeleton. */
function palmAt(bones,side,target) {
  const upper=bones[`upperarm_${side}`],lower=bones[`lowerarm_${side}`],hand=bones[`hand_${side}`]
  const finger=bones[`middle_01_${side}`]
  const s=upper.getWorldPosition(new THREE.Vector3()),e=lower.getWorldPosition(new THREE.Vector3()),w=hand.getWorldPosition(new THREE.Vector3())
  const palm=w.clone().lerp(finger.getWorldPosition(new THREE.Vector3()),.72)
  const handRotation=hand.getWorldQuaternion(new THREE.Quaternion())
  const wrist=target.clone().sub(palm.sub(w)),axis=wrist.clone().sub(s)
  const l1=s.distanceTo(e),l2=e.distanceTo(w),distance=THREE.MathUtils.clamp(axis.length(),Math.abs(l1-l2)+1e-5,l1+l2-1e-5)
  axis.normalize();wrist.copy(s).addScaledVector(axis,distance)
  const pole=e.clone().sub(s);pole.addScaledVector(axis,-pole.dot(axis))
  if(pole.lengthSq()<1e-10){pole.set(0,-1,0);pole.addScaledVector(axis,-pole.dot(axis))}
  const along=(l1*l1-l2*l2+distance*distance)/(2*distance)
  const elbow=s.clone().addScaledVector(axis,along).addScaledVector(pole.normalize(),Math.sqrt(Math.max(0,l1*l1-along*along)))
  rotateToward(upper,e.clone().sub(s),elbow.clone().sub(s))
  const actualElbow=lower.getWorldPosition(new THREE.Vector3())
  rotateToward(lower,hand.getWorldPosition(new THREE.Vector3()).sub(actualElbow),wrist.sub(actualElbow))
  hand.quaternion.copy(hand.parent.getWorldQuaternion(new THREE.Quaternion()).invert().multiply(handRotation))
  hand.updateWorldMatrix(false,true)
}

/** Studio owns this clone's ball. The shared Tactics court still owns its single
 * match ball and is never changed by this presentation adapter. */
export function presentCarryBall(rig,visible) {
  const mesh=rig.group.getObjectByName('Movement_Ball')
  mesh.visible=visible
  if(!visible)return
  const bones=rig.bone,ball=bones.Ball_Control
  ball.scale.setScalar(1)
  rig.group.updateWorldMatrix(true,true)
  const palms=['l','r'].map(side=>bones[`hand_${side}`].getWorldPosition(new THREE.Vector3())
    .lerp(bones[`middle_01_${side}`].getWorldPosition(new THREE.Vector3()),.72))
  const center=palms[0].clone().add(palms[1]).multiplyScalar(.5)
  const across=palms[0].clone().sub(palms[1]).normalize()
  const radius=.11*ball.getWorldScale(new THREE.Vector3()).x
  for(const [i,side] of ['l','r'].entries())palmAt(bones,side,center.clone().addScaledVector(across,i===0?radius:-radius))
  ball.position.copy(ball.parent.worldToLocal(center));ball.updateWorldMatrix(false,true)
}
