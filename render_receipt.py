"""What a render run may claim about itself, with no Blender in it.

The renderer's console line is what a person and a script both read first. It
said PASS whenever the function reached its end, which is not the same as
having rendered or measured anything.

`--no-stills` without `--animate` skips the phase loop entirely. Run that way
over the eight drills it printed PASS eight times and wrote eight receipts
carrying zero phases. The receipts were honest; the word was not.

This is the same fault this lane reports in other instruments, in its own file:
an absence of measurement read as a clean result. It lives here so that a test
can call it, because the renderer imports `bpy` and its tests skip.
"""

from __future__ import annotations

PASS = "PASS"
NOTHING_RENDERED = "NOTHING RENDERED"


def render_outcome(phase_count: int, animation: object | None) -> str:
    """PASS only when the run actually produced something.

    A run that posed no phase and exported no animation has measured nothing.
    It has not failed either, and it must not say so, because a legitimate
    `--turntable`-only or `--animate`-only run is not a defect. It says what
    happened, which is that nothing was rendered.
    """
    if phase_count <= 0 and not animation:
        return NOTHING_RENDERED
    return PASS


# THE EXIT CODE IS 0 EITHER WAY, and a script must not read it as a result.
# NOTHING RENDERED is not a failure: a turntable-only or animation-only run is
# legitimate, and so is a phase filter that matches nothing in this job. The
# renderer exits non-zero only when it actually raises.
#
# So a caller that wants to know whether anything was measured must read the
# receipt's `phases`, or match this word on the console. Reading the exit code
# alone is how eight empty runs looked like eight clean ones.
