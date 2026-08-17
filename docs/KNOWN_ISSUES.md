# Known issues

## Reference catch is not yet a final coaching sample

The current MPFB catch render remains an intermediate calibration artifact. Its hand orientation
in the locked reference view was visually approved on 2026-08-17, but presentation and final
coaching-sample acceptance are still pending.

The MPFB hands deliberately retain the signed local index-to-pinky cross product from the rig.
Normalising that sign across left and right hands produces the rejected two-left-hands projection.
The Blender integration test locks the approved thumb side and hand-plane error for both hands.

Do not set `--reference-compared` or publish the current generated pose.

## Fingertip evidence is soft guidance

The supplied photograph is blurred and fingers overlap. Earlier hard per-pixel fingertip IK
produced anatomically painful joints even while reporting low pixel error. Finger targets now guide
comparison, but joint limits and visual anatomy take priority over exact fingertip pixels.

## Presentation is deferred

Clothing, materials, lighting, background, and final rendering style are intentionally deferred
until pose meaning and anatomy are accepted.

## Reference media is local-only

The source photograph is not committed because publication rights have not been established. The
configuration records its SHA-256 and dimensions so an authorised local copy can be verified.
