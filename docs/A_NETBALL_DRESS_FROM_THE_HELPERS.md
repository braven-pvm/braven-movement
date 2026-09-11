# A netball dress from the basemesh helpers

Clark, the character and animation lane. Written on 10 September 2026, the day
the dress was made. This is the record of one route to a sports kit: cut the
garment out of the MakeHuman basemesh helper meshes with planes, write it as an
MPFB `.mhclo`, and let the pipeline wear it like any shipped garment. Two other
routes were tried by other lanes on the same day, a kit painted into the skin
texture and a skirt under cloth simulation; this document is one of the three
and does not compare them.

Marius's direction, verbatim: "sports kit, tight fitting, short skirts, models
should not be too curvy but must be sporty, but athletic", then "the hotpants
can be a bit shorter, and the skirt a bit longer, and I mean a bit - when
standing upright the hotpants should not stick out, but when bending which
would normally reveal their genitals/bum, the hotpants should cover it", then
"the skirt must be 'softer' material - it now looks like flaring cone - it
should drape over her body naturally and/or be more tightly fit".

## 1. What is in the repository

| File | What it is |
| --- | --- |
| `config/kit/netball_dress.v1.json` | Every number of the dress. Hems, ease, straps, neckline, the UV frame, the bib square. |
| `scripts/author_netball_dress.py` | The Blender script that cuts the helpers by those numbers and writes the `.mhclo`. |
| `scripts/make_bib_image.py` | Draws the bib square with the position letters into the dress's UV frame. |
| `scripts/kit_studio_sheet.py` | Ten studio views, standing and in a drill phase, plus the skirt clearance measurement. |
| `assets/kit/braven_netball_dress.mhclo`, `.obj` | The dress, 1477 bodysuit vertices and 252 skirt vertices, all triangles. |
| `assets/kit/braven_netball_dress.build.json` | The sidecar: landmarks, counts, the check, the hashes of the two inputs and of the two outputs, seconds per stage, and the provenance claim `readsNoSkin: true` with `derivedFrom`. |
| `assets/kit/bib_GS.png`, `.json` | The bib image for a goal shooter, and its sidecar with the same claim and the output hash. |
| `config/netball_kit.v1.json` | The reference config with `presentation.kit` set: the dress, the bib, a sock top, team green. |

The pipeline reads three optional keys under `presentation.kit`: `garment`,
`bibImage` and `sockTopM`. A config without them builds the figure it always
built. A kit path is refused anywhere but under `assets/kit/`, at load time.
`docs/LICENSING.md` carries a bullet for that directory and
`asset_licences.py` quotes it, so a receipt that wears the dress records the
file, its sha256 and the owner's line, and refuses nothing it should not.

## 2. The process, from nothing to a fitted dress

1. Build the athlete of the reference config with `create_athlete`. The
   authoring config must name no garment, because this script makes one.
2. Extract the `helper-tights` group (2674 vertices, a whole-body suit with
   arms) and the `helper-skirt` group (720 vertices, a cone from the hips to
   the ankle) with `ObjectService.extract_vertex_group_to_new_object`. Deselect
   everything before each call. The extractor enters edit mode with everything
   selected and deletes the inverse of the group, which wipes the object the
   previous call made. That cost the first hour.
3. Read landmarks: the shoulder joint from `world_head(rig, "upperarm_l")`,
   the shoulder top at the strap edge, the throat front and the back from the
   helper vertices. The recorded values are in the sidecar.
4. Cut the bodysuit. Every cut is `bmesh.ops.bisect_plane` with no clearing.
   Briefs hem, top, arm at |x| 0.205, a tilted armhole plane per side from the
   strap edge to below the armpit, two front neckline planes per side and one
   back plane per side. Then each face is kept or deleted by where its centroid
   lies against every plane at once.
5. Cut the skirt at the hem the same way, then hang it: each vertex moves out
   to the widest body radius above it, in 72 angular bins interpolated
   between centres, plus 1.2 cm of ease that blends to zero at the waist ring.
   Rename its vertex group to `body`, so the `.mhclo` matching pairs it with
   skin vertices and the skirt moves with the thighs in a landing.
6. Delete loose vertices, prune each vertex to one vertex group, triangulate,
   and lay a planar UV map: front faces on the left half of the image, back
   faces mirrored on the right, x across and z up in `uvFrame`.
7. Join the two parts. `ClothesService.mesh_is_valid_as_clothes` must pass.
   `ClothesService.create_mhclo_from_clothes_matching` matches every vertex to
   three basemesh vertices with offsets, and `write_mhclo` writes the `.mhclo`
   and the `.obj`. The matching needs the basemesh cross-reference cache; the
   script builds it once (20.5 s) if the directory is empty.
8. Wear it: `--config config/netball_kit.v1.json` on `blender_movement_render.py`
   or on `scripts/kit_studio_sheet.py`. `create_athlete` loads the garment into
   the suit slot, cuts the shoe's sock at `sockTopM` and closes the ring, and
   `make_fabric_material` mixes the bib image over the fabric colour by its
   alpha.

## 3. What the check refuses, and what broke on the way

`mesh_is_valid_as_clothes` refuses three things: a vertex on no face, mixed
face types, and a vertex in more than one vertex group. Delete vertices with
zero faces, not fewer than two, which ate the shoulder straps; triangulate;
prune.

The MakeClothes operators are not registered in background mode. The script
calls the services they wrap.

A coordinate cut on a quad mesh stair-steps at every edge. Six sites showed it
in one render: neckline, shoulder, armhole, hem, briefs hem, sock cuff. A snap
of the boundary vertices onto the plane stretched the faces instead. A plane
bisect gives a level edge. A cut limited to a band of the mesh deleted
centre-line vertices that the faces of the other side still used, and the
neckline came back notched twice. Split on every plane first, then classify
faces: that is the method that was left standing after twelve builds.

A sphere armhole left a ragged bare patch on the back of the shoulder. Planes
only.

The skirt helper sits 1 to 2 cm off the thigh at the front. In the absorb
phase of `netball_double_foot_landing` the thigh pushed through it, and the
intersection read as a torn hem. A flare fixed it and read as a cone. The
hang from the widest hip point with ease fixed both, and the clearance
instrument now reads it: 252 skirt vertices, none inside the skin at rest or
in absorb, closest approach 8.8 mm.

No shoe asset carries a low sock; all six MPFB shoe assets are one mesh with
a sock to mid-calf. `trim_sock` cuts it at `sockTopM` and fills the ring.
`shoes05` itself has two collar quads whose calf and foot weights stretch them
to 6.8 cm in dorsiflexion, a pale wedge over the laces in every absorb side
render, the untrimmed shoe included. That is the shipped asset and not the
kit.

## 4. The numbers

Authoring, one Blender session on this machine, from the sidecar: athlete
4.5 s, cuts 0.2 s, check and match and write 2.6 s, 7.4 s in all after
Blender and MPFB start (about 30 s). Ten studio views with EEVEE, about
95 s. The receipted landing, two phases and three views, 100 to 111 s.

Wall clock for dress one, from the first variant config at 09:40 to the
twelfth build through the receipted path at 12:12: 2 h 32 min, with three
rounds of direction from Marius and every fault above inside it. The first
fitted dress went through the receipted path at 10:47.

## 5. Kit two

The same garment with other numbers is an edit of `config/kit/` and three
runs of about 2.5 min each with a look at every panel: 30 to 60 min. A
different garment type, two pieces, a collar or a sleeve, is half a day,
because each new cut is a plane to place and to look at. These are
estimates and not measurements.

The colour is `presentation.kit.baseColor`. The bib letters are one argument
to `make_bib_image.py`. What is not a parameter yet: bodice ease (the helper
is skin-tight), a sleeve (the arm cut alone gave a cap sleeve in one build),
and any panel design beyond one colour.

## 6. What this route does not give

No cloth dynamics: a skirt in flight hangs as if standing. Plane cuts give
polygonal necklines; a round scoop needs more planes. The helpers limit the
garment to a skin offset, so no pleats, no collar, no loose sleeve without
modelling. And every iteration needs a person to read the renders; the
clearance number catches the thigh, and nothing yet catches a torn edge.
