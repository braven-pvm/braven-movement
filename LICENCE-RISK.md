# Licence risk, and what has to happen before this is sold

## The decision

On 18 August 2026 Marius decided to bring SMPL-X in under its **research
licence**, so that the figures in generated manual content can be an athletic
woman rather than the single body MHR ships with. The decision was made
knowingly, and this file exists so it is not forgotten.

> **Before any commercial use, SMPL-X needs a commercial licence from the Max
> Planck Institute for Intelligent Systems.** The research licence does not
> cover selling a product, selling content produced with it, or using it inside
> a paying engagement.

That covers manual content sold or supplied to a client, analysis delivered as
a paid service, and anything built on top of it for the lab's customers.

## Why SMPL-X is being brought in at all

MHR ships one body and no way to change it. Its 68 shape parameters are all
skeletal: bone lengths, shoulder width, hip width. The only shape vectors in
`mhr_model.pt` are 72 face expressions. Measured on the reference body, the
shoulders are 44.9 cm across and the build reads as a heavy adult male. Nothing
in the model can make it otherwise.

SMPL-X carries a real identity space, separate female and male models, and is
the standard body model in biomechanics, which also matters for the analysis
work later.

## What is still MHR, and stays MHR

The engine does not move to SMPL-X. Everything measured and validated is on
MHR and stays there:

- the joint limits the athlete is solved against, which are the model's own
- the ISB joint angles, validated against OpenSim to six decimal places
- the coaching bands, the retargeting, the possession model

SMPL-X is used for the **figure**, not for the solve. The solved MHR pose is
retargeted onto an SMPL-X body for rendering. That keeps every validated number
where it was and confines the new licence to content production, which is also
where the commercial exposure is easiest to reason about.

If the engine itself ever moves to SMPL-X, the joint limits, the angle
definitions and every band would have to be revalidated against it. That is a
much larger piece of work than it looks, and nothing here requires it.

## What is needed, and who can get it

The model files are behind a registration and a licence acceptance at
`https://smpl-x.is.tue.mpg.de`. They cannot be fetched automatically and I have
not tried. A person has to register, accept the licence, and download:

- `SMPLX_FEMALE.npz` at minimum
- `SMPLX_MALE.npz` and `SMPLX_NEUTRAL.npz` if male and neutral figures are
  wanted later

Put them in `spikes/smplx-assets/`, which is in `.gitignore`. **Do not commit
the model files.** The licence does not permit redistribution, and a public or
shared repository holding them is a breach on its own.
