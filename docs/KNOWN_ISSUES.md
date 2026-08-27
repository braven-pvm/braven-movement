# Known issues

## Reference catch is not yet a final coaching sample

The current MPFB catch render remains a review artifact. Its hand orientation in the locked
reference view was visually approved on 2026-08-17 and the first premium coaching-studio
presentation pass is complete, but final coaching-sample acceptance is still pending.

The athlete now has a deliberately lean-muscular MPFB phenotype, a loaded lower-body stance,
forward torso intent, and a restrained concentration expression. These parameters are repeatable
and receipt-backed, but MPFB's base topology and identity still limit fine facial acting and
sport-specific muscle definition. The Faceunits 01 pack is a required authoring dependency.

The MPFB hands deliberately retain the signed local index-to-pinky cross product from the rig.
Normalising that sign across left and right hands produces the rejected two-left-hands projection.
The Blender integration test locks the approved thumb side and hand-plane error for both hands.

Do not set `--reference-compared` or publish the current generated pose.

## Fingertip evidence is soft guidance

The supplied photograph is blurred and fingers overlap. Earlier hard per-pixel fingertip IK
produced anatomically painful joints even while reporting low pixel error. Finger targets now guide
comparison, but joint limits and visual anatomy take priority over exact fingertip pixels.

## Presentation is ready for review, not final publication

The deterministic presentation now includes a graphite training kit, sports trainers, a curved
blue-grey studio background, a four-light rig, and a regulation-scale three-colour panelled
netball with embossed seams and procedural grip. The athlete identity, final branded kit, ball
artwork, and production colour grade remain intentionally replaceable through the versioned
configuration after coaching acceptance.

## Reference media is local-only

The source photograph is not committed because publication rights have not been established. The
configuration records its SHA-256 and dimensions so an authorised local copy can be verified.
