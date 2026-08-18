"""Wear the solved MHR pose on an SMPL-X body.

The engine solves on MHR and that does not change: the joint limits, the ISB
angles validated against OpenSim and every coaching band were measured there.
What changes is the body a person looks at. MHR has one, and it is not the
athlete these manuals are for.

The two models do not share a skeleton. MHR has 127 joints and SMPL-X has 55,
with different names and different rest orientations, so the pose is not
transferred, it is fitted: SMPL-X is posed until its joint centres sit on
MHR's. Forty correspondences do it, and the fifteen finger joints in each hand
are what pin the forearm twist, which a bone direction on its own leaves free.

Only the joints matter for the fit, so it runs on forward kinematics and never
touches the mesh. The mesh is skinned once at the end, for drawing.

Licence: SMPL-X is in under its research licence. Refer to LICENCE-RISK.md.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from smplx_body import JOINTS, Smplx

# SMPL-X is published in metres and this repository works in centimetres.
METRES_TO_CM = 100.0

# Which MHR joint each SMPL-X joint sits on.
#
# Only the joints that mean the same thing in both models. The spine chain, the
# collars and the head are left out on purpose: the two models put them in
# different places, and asking them to coincide distorts everything around
# them. Measured on the fitted body, SMPL-X's collar to shoulder bone is 9.7 cm
# where MHR's is 17.7, and its spine3 to neck is 5.1 where MHR's is 18.5. Left
# free, they settle wherever the pelvis and the shoulders put them, which is
# what a spine does anyway.
#
# The balls of the feet are in for the same reason the knuckles are in: an
# ankle with nothing below it has no observed rotation, so the optimiser
# leaves the foot wherever it started and the athlete stands on pointed toes.
# SMPL-X's ankle to toe bone is 12.1 cm where MHR's is 14.8, an eighteen per
# cent difference, which is the same order as the bones already in this list
# and nothing like the collar's eighty two.
#
# The hands run index, middle, pinky, ring, thumb in SMPL-X's order, which is
# not the order they are in on a hand.
CORRESPONDENCE = {
    0: "root",
    1: "l_upleg", 2: "r_upleg",
    4: "l_lowleg", 5: "r_lowleg",
    7: "l_foot", 8: "r_foot",
    10: "l_ball", 11: "r_ball",
    12: "c_neck",
    16: "l_uparm", 17: "r_uparm",
    18: "l_lowarm", 19: "r_lowarm",
    20: "l_wrist", 21: "r_wrist",
}
for offset, side in ((25, "l"), (40, "r")):
    for number, finger in enumerate(("index", "middle", "pinky", "ring", "thumb")):
        for segment in range(3):
            CORRESPONDENCE[offset + number * 3 + segment] = (
                f"{side}_{finger}{segment + 1}"
            )

# A hand has thirty joints in this list and a body has thirteen, so without
# this the fingers decide where the body goes.
BODY_WEIGHT = 12.0

# An athletic woman, in SMPL-X shape coefficients. The first coefficient is
# height and the second is build: measured on this model, the first runs 151.6
# to 179.8 cm across its range, and the second takes the waist from 26.9 to
# 40.0 cm without changing height.
ATHLETIC_FEMALE = np.array([0.4, -1.5, 0.2, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])


# How lean the build coefficient is pushed after the proportions are fitted.
# The second coefficient takes the waist from 26.9 to 40.0 cm without changing
# height, and fitting bone lengths alone says nothing about it.
LEAN = -1.4


class RetargetError(RuntimeError):
    pass


def usable(model: Smplx, index: dict[str, int]) -> dict[int, int]:
    """Return the correspondences both skeletons actually have."""
    found = {
        smplx: index[mhr]
        for smplx, mhr in CORRESPONDENCE.items()
        if mhr in index and smplx < JOINTS
    }
    if len(found) < 12:
        raise RetargetError(
            f"only {len(found)} joints correspond, which is not enough to pose "
            "a body. Check the MHR joint names."
        )
    return found


def fit_shape(
    model: Smplx,
    rest_joints: np.ndarray,
    index: dict[str, int],
    lean: float = LEAN,
    passes: int = 300,
) -> np.ndarray:
    """Return the identity whose bones are the same lengths as this athlete's.

    Done once. Without it the two skeletons have different limb lengths and no
    pose can put their joints in the same places: the fit came out 9.5 cm off
    at the worst joint because it was being asked for something impossible.

    Bone lengths, not joint positions. The first attempt compared the two rest
    poses directly and produced a 131 cm body for a 173 cm athlete, because MHR
    rests in a T pose and SMPL-X rests with the arms down: it was distorting
    the body to account for a difference of pose. A bone length does not care
    how the body is standing.

    Build is not something a bone length knows about, so it is set afterwards.
    """
    import torch

    pairs = usable(model, index)
    bones = [
        (joint, int(model.parents[joint]))
        for joint in sorted(pairs)
        if int(model.parents[joint]) in pairs
    ]
    if len(bones) < 10:
        raise RetargetError(f"only {len(bones)} bones correspond")
    wanted = torch.tensor(
        [
            float(
                np.linalg.norm(rest_joints[pairs[j]] - rest_joints[pairs[p]])
            )
            / METRES_TO_CM
            for j, p in bones
        ],
        dtype=torch.float64,
    )

    template = torch.tensor(model.template, dtype=torch.float64)
    directions = torch.tensor(model.shape_directions, dtype=torch.float64)
    regressor = torch.tensor(model.joint_regressor, dtype=torch.float64)
    weights = torch.tensor(
        [1.0 if j >= 25 else BODY_WEIGHT for j, _ in bones], dtype=torch.float64
    )
    children = torch.tensor([j for j, _ in bones], dtype=torch.long)
    parents = torch.tensor([p for _, p in bones], dtype=torch.long)
    beta = torch.zeros(directions.shape[2], dtype=torch.float64, requires_grad=True)

    optimiser = torch.optim.LBFGS(
        [beta], max_iter=passes, line_search_fn="strong_wolfe"
    )

    def closure():
        optimiser.zero_grad()
        vertices = template + torch.einsum("vdc,c->vd", directions, beta)
        joints = regressor @ vertices
        lengths = (joints[children] - joints[parents]).norm(dim=-1)
        # Held near the mean body. These are standard deviations of a
        # population, so a coefficient past about three is a body that does not
        # occur, and the first attempt went to ten.
        loss = (weights * (lengths - wanted) ** 2).sum() + 0.02 * (beta**2).sum()
        loss.backward()
        return loss

    optimiser.step(closure)
    found = beta.detach().numpy().copy()
    found = np.clip(found, -3.0, 3.0)
    # Lean is a choice, not a measurement, so it is applied on top and said so.
    found[1] = lean
    return found


@dataclass(frozen=True)
class Fitted:
    """One posed body."""

    vertices: np.ndarray
    joints: np.ndarray
    worst_joint_error_cm: float
    mean_joint_error_cm: float


def _rodrigues(theta):
    """Axis angle to rotation matrix, batched, in torch."""
    import torch

    angle = torch.norm(theta, dim=-1, keepdim=True).clamp(min=1e-8)
    axis = theta / angle
    x, y, z = axis[..., 0], axis[..., 1], axis[..., 2]
    zero = torch.zeros_like(x)
    skew = torch.stack(
        [zero, -z, y, z, zero, -x, -y, x, zero], dim=-1
    ).reshape(*theta.shape[:-1], 3, 3)
    eye = torch.eye(3, dtype=theta.dtype, device=theta.device).expand_as(skew)
    sin = torch.sin(angle).unsqueeze(-1)
    cos = torch.cos(angle).unsqueeze(-1)
    return eye + sin * skew + (1 - cos) * (skew @ skew)


def _forward(rest_joints, parents, theta, translation):
    """Pose the skeleton. Returns the joint centres and each joint's rotation."""
    import torch

    rotations = _rodrigues(theta)
    posed = [rest_joints[0] + translation]
    globals_ = [rotations[0]]
    for joint in range(1, len(parents)):
        parent = int(parents[joint])
        offset = rest_joints[joint] - rest_joints[parent]
        globals_.append(globals_[parent] @ rotations[joint])
        posed.append(posed[parent] + globals_[parent] @ offset)
    return torch.stack(posed), torch.stack(globals_)


def fit(
    model: Smplx,
    mhr_joints: np.ndarray,
    index: dict[str, int],
    shape: np.ndarray | None = None,
    passes: int = 90,
    start=None,
):
    """Pose an SMPL-X body so its joints sit on these MHR joints.

    Returns the pose and translation, in SMPL-X's own units, along with how far
    off it finished. The previous frame's answer makes a good starting point
    and is what keeps a sequence from flickering.
    """
    import torch

    pairs = usable(model, index)
    shaped, rest = model.body(ATHLETIC_FEMALE if shape is None else shape)
    rest_t = torch.tensor(rest, dtype=torch.float64)
    parents = model.parents
    target = torch.tensor(
        np.array([mhr_joints[pairs[s]] for s in sorted(pairs)]) / METRES_TO_CM,
        dtype=torch.float64,
    )
    rows = torch.tensor(sorted(pairs), dtype=torch.long)
    pull = torch.tensor(
        [[1.0 if s >= 25 else BODY_WEIGHT] for s in sorted(pairs)],
        dtype=torch.float64,
    )

    theta = torch.zeros((JOINTS, 3), dtype=torch.float64, requires_grad=True)
    translation = torch.zeros(3, dtype=torch.float64, requires_grad=True)
    if start is not None:
        with torch.no_grad():
            theta.copy_(torch.tensor(start[0], dtype=torch.float64))
            translation.copy_(torch.tensor(start[1], dtype=torch.float64))

    optimiser = torch.optim.LBFGS(
        [theta, translation], max_iter=passes, line_search_fn="strong_wolfe"
    )

    def closure():
        optimiser.zero_grad()
        posed, _ = _forward(rest_t, parents, theta, translation)
        # A light pull toward the rest pose, so joints nothing corresponds to
        # stay where they were instead of wandering.
        loss = (
            (pull * (posed[rows] - target) ** 2).sum() + 1e-4 * (theta**2).sum()
        )
        loss.backward()
        return loss

    optimiser.step(closure)
    with torch.no_grad():
        posed, globals_ = _forward(rest_t, parents, theta, translation)
        error = (posed[rows] - target).norm(dim=-1) * METRES_TO_CM
    return (
        theta.detach().numpy(),
        translation.detach().numpy(),
        float(error.max()),
        float(error.mean()),
        shaped,
        rest,
    )


def skin(model: Smplx, shaped, rest, theta, translation) -> np.ndarray:
    """Return the posed mesh, in centimetres, for drawing."""
    import torch

    rest_t = torch.tensor(rest, dtype=torch.float64)
    with torch.no_grad():
        posed, globals_ = _forward(
            rest_t,
            model.parents,
            torch.tensor(theta, dtype=torch.float64),
            torch.tensor(translation, dtype=torch.float64),
        )
        # The transform each joint applies: rotate about its rest position,
        # then move to where it ended up.
        offsets = posed - torch.einsum("jab,jb->ja", globals_, rest_t)
        weights = torch.tensor(model.weights, dtype=torch.float64)
        rotation = torch.einsum("vj,jab->vab", weights, globals_)
        shift = weights @ offsets
        vertices = (
            torch.einsum("vab,vb->va", rotation, torch.tensor(shaped)) + shift
        )
    return vertices.numpy() * METRES_TO_CM
