# Known issues

## Reference catch is not accepted

The current MPFB catch render is an intermediate calibration artifact, not an approved coaching
sample. Ball, elbow, and wrist landmarks were matched closely, but the upper/right hand still
reads visually like a second left hand. Its local index-to-pinky basis and thumb-side convention
must be corrected before further visual matching.

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
