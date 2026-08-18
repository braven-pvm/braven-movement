"""An SMPL-X body, for drawing the athlete rather than for solving her.

MHR ships one body and no way to change its build. Every one of its 68 shape
parameters is skeletal, and the only shape vectors in its model file are 72
face expressions. The figure in a manual has to look like the athlete the
manual is for, and MHR cannot do that.

SMPL-X carries a real identity space and separate female and male models. It is
used here for the figure only. The solve stays on MHR, because that is where
the joint limits, the ISB angles validated against OpenSim, and every coaching
band were measured, and moving the solver would mean revalidating all of it.

Licence
-------

SMPL-X is in under its **research licence**. Commercial use needs a licence
from the Max Planck Institute, and `LICENCE-RISK.md` at the repository root
says what that covers. The model files are not in this repository and must not
be committed: the licence does not permit redistribution.

Getting the files
-----------------

They are behind a registration at `https://smpl-x.is.tue.mpg.de`. Register,
accept the licence, download, and put the `.npz` files in `smplx-assets/`
beside this file. `SMPLX_FEMALE.npz` is the one this needs.

Everything in this module asserts the shape of what it loaded rather than
trusting it, because it was written before the file was available and a wrong
assumption should fail loudly rather than draw a subtly wrong body.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

SPIKE_DIR = Path(__file__).resolve().parent
ASSETS = SPIKE_DIR / "smplx-assets"
FEMALE = "SMPLX_FEMALE.npz"

# SMPL-X, as published. Asserted on load rather than assumed.
VERTICES = 10475
JOINTS = 55
# The identity coefficients actually used. The model carries 400 shape
# directions, of which the first 300 are identity and the rest expression, and
# ten is what fits a body without chasing noise.
SHAPE_COEFFICIENTS = 10


class SmplxError(RuntimeError):
    pass


def missing() -> str | None:
    """Return why the body cannot be loaded, or None if it can."""
    path = ASSETS / FEMALE
    if not path.is_file():
        return (
            f"{path} is not here. SMPL-X is behind a registration at "
            "https://smpl-x.is.tue.mpg.de and cannot be fetched automatically. "
            "Register, accept the licence, download SMPLX_FEMALE.npz and put it "
            "in that folder. Do not commit it: the licence does not permit "
            "redistribution. Refer to LICENCE-RISK.md."
        )
    return None


@dataclass(frozen=True)
class Smplx:
    """The parts of an SMPL-X model this needs, and nothing else."""

    template: np.ndarray        # (VERTICES, 3) the mean body
    shape_directions: np.ndarray  # (VERTICES, 3, SHAPE_COEFFICIENTS)
    joint_regressor: np.ndarray   # (JOINTS, VERTICES)
    weights: np.ndarray           # (VERTICES, JOINTS) skinning
    parents: np.ndarray           # (JOINTS,) kinematic tree
    faces: np.ndarray             # (triangles, 3)

    def body(self, shape: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Return the rest vertices and joint centres for this identity.

        Pose is not applied here. The figure is posed by retargeting, which is
        a separate step and a separate problem.
        """
        coefficients = np.asarray(shape, dtype=np.float64).reshape(-1)
        if coefficients.size != SHAPE_COEFFICIENTS:
            raise SmplxError(
                f"expected {SHAPE_COEFFICIENTS} shape coefficients, got "
                f"{coefficients.size}"
            )
        vertices = self.template + np.einsum(
            "vdc,c->vd", self.shape_directions, coefficients
        )
        return vertices, self.joint_regressor @ vertices


def decimate(vertices: np.ndarray, faces: np.ndarray, grid_cm: float = 1.6):
    """Merge vertices onto a grid, for drawing only.

    SMPL-X carries 10475 vertices and 20908 faces, which is right for research
    and far too much for a figure 300 pixels wide: eight pages came to four and
    a half megabytes and 690 thousand triangle fills. At 1.6 cm the silhouette
    is unchanged at that size and the page is a fifth of the weight.

    Returns the merged vertices, the rebuilt faces, and the mapping, so a posed
    mesh can be reduced the same way every frame without redoing the search.
    """
    keys = np.round(np.asarray(vertices, dtype=np.float64) / grid_cm).astype(np.int64)
    _, first, inverse = np.unique(keys, axis=0, return_index=True, return_inverse=True)
    remapped = inverse[np.asarray(faces)]
    # A face whose corners merged into fewer than three vertices has no area.
    keep = (
        (remapped[:, 0] != remapped[:, 1])
        & (remapped[:, 1] != remapped[:, 2])
        & (remapped[:, 0] != remapped[:, 2])
    )
    return inverse, remapped[keep]


def _pick(data, *names: str) -> np.ndarray:
    for name in names:
        if name in data:
            return np.asarray(data[name])
    raise SmplxError(
        f"the model file has none of {names}. It has: {sorted(data.files)}"
    )


def load(path: Path | None = None) -> Smplx:
    """Load the female body, checking every assumption about its shape."""
    source = (ASSETS / FEMALE) if path is None else Path(path)
    reason = missing() if path is None else None
    if reason:
        raise SmplxError(reason)
    if not source.is_file():
        raise SmplxError(f"{source} is not here")

    data = np.load(source, allow_pickle=True)
    template = _pick(data, "v_template").astype(np.float64)
    directions = _pick(data, "shapedirs").astype(np.float64)
    regressor = _pick(data, "J_regressor").astype(np.float64)
    weights = _pick(data, "weights", "lbs_weights").astype(np.float64)
    tree = _pick(data, "kintree_table").astype(np.int64)
    faces = _pick(data, "f", "faces").astype(np.int64)

    if template.shape != (VERTICES, 3):
        raise SmplxError(
            f"expected a {VERTICES} vertex template, got {template.shape}. "
            "SMPL has 6890 and SMPL-H 10475 without the face; check which "
            "model was downloaded."
        )
    if directions.ndim != 3 or directions.shape[:2] != (VERTICES, 3):
        raise SmplxError(f"shapedirs is {directions.shape}, expected (V, 3, n)")
    if directions.shape[2] < SHAPE_COEFFICIENTS:
        raise SmplxError(
            f"shapedirs carries {directions.shape[2]} directions, fewer than "
            f"the {SHAPE_COEFFICIENTS} this uses"
        )
    if regressor.shape != (JOINTS, VERTICES):
        raise SmplxError(
            f"J_regressor is {regressor.shape}, expected ({JOINTS}, {VERTICES})"
        )
    if weights.shape != (VERTICES, JOINTS):
        raise SmplxError(
            f"skinning weights are {weights.shape}, expected "
            f"({VERTICES}, {JOINTS})"
        )
    if tree.shape[0] != 2 or tree.shape[1] != JOINTS:
        raise SmplxError(f"kintree_table is {tree.shape}, expected (2, {JOINTS})")

    return Smplx(
        template=template,
        shape_directions=directions[:, :, :SHAPE_COEFFICIENTS],
        joint_regressor=regressor,
        weights=weights,
        # The root's parent is published as a very large number. Minus one is
        # what every walk of the tree below expects.
        parents=np.where(tree[0] < 0, -1, tree[0]).astype(np.int64),
        faces=faces,
    )
