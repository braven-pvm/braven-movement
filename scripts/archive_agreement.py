"""Does this tree still solve what the archived figures were drawn from?

Every two-bodies number compares an ENGINE side solved on this tree against a
RENDERED side read from an archived receipt. That comparison is only meaningful
while the two sides come from the same solve, and the receipt records the proof:
`jobSha256` is the hash of the job file the render consumed.

THE CLAIM WAS LOAD BEARING AND UNCHECKED. Three instruments and two papers state
"every job file on this tree is byte-identical to the `jobSha256` its receipt
recorded". It was true when each was written, and nothing read it afterwards. A
job file changing under a lane would leave every published number comparing two
different solves, silently, with the papers still asserting they agree.

So this refuses rather than reports. An instrument that prints a warning and
then prints its table has published the numbers anyway.

    from archive_agreement import refuse_if_the_tree_has_moved
    refuse_if_the_tree_has_moved(archive_directory, jobs_directory)
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

JOBS = Path(__file__).resolve().parents[1] / "spikes" / "poc-output"


def job_agreement(archive: Path, jobs: Path = JOBS) -> dict:
    """Compare each receipt's recorded job hash against the job file on disk.

    Returns the three groups by name, so a caller can say WHICH drill moved
    rather than only how many did.
    """
    identical: list[str] = []
    moved: list[tuple[str, str, str]] = []
    absent: list[str] = []
    stamps: set[str] = set()
    for path in sorted(archive.glob("*.render.json")):
        receipt = json.loads(path.read_text(encoding="utf-8"))
        movement_id = receipt["movementId"]
        stamps.add(json.dumps(receipt.get("generatedFrom"), sort_keys=True))
        job = jobs / f"{movement_id}.job.json"
        if not job.is_file():
            absent.append(movement_id)
            continue
        recorded = receipt["jobSha256"]
        found = hashlib.sha256(job.read_bytes()).hexdigest()
        if found == recorded:
            identical.append(movement_id)
        else:
            moved.append((movement_id, recorded, found))
    return {"identical": identical, "moved": moved, "absent": absent,
            "stamps": sorted(stamps)}


def refuse_if_the_tree_has_moved(archive: Path, jobs: Path = JOBS) -> dict:
    """Raise unless every archived receipt's job is byte-identical on this tree.

    A MISSING job file is refused as firmly as a changed one. It is the same
    failure with less evidence: nothing on this tree can be shown to be the
    solve that drew the figure.

    A second build stamp in one archive is refused too, because two render
    processes cannot make one archive, and `spikes/archive_receipts.py` states
    that rule for the archive it builds.
    """
    result = job_agreement(archive, jobs)
    if result["moved"]:
        lines = [f"    {name}\n        receipt {recorded}\n        tree    {found}"
                 for name, recorded, found in result["moved"]]
        raise SystemExit(
            "REFUSED. The job files have moved since these figures were drawn, so "
            "the engine side solved here is NOT the solve the rendered side came "
            f"from:\n" + "\n".join(lines))
    if result["absent"]:
        raise SystemExit(
            "REFUSED. No job file on this tree for: "
            + ", ".join(result["absent"])
            + ". Nothing here can be shown to be the solve that drew the figure.")
    if len(result["stamps"]) > 1:
        raise SystemExit(
            f"REFUSED. {len(result['stamps'])} distinct build stamps in {archive}. "
            "Two render processes cannot make one archive, so these receipts are "
            "not one build and must not be read as one.")
    if not result["identical"]:
        raise SystemExit(f"REFUSED. No receipts found in {archive}.")
    return result


def state_the_agreement(archive: Path, jobs: Path = JOBS) -> None:
    """Print the check's verdict, so a table carries its own warrant."""
    result = refuse_if_the_tree_has_moved(archive, jobs)
    print(f"{len(result['identical'])} of {len(result['identical'])} job files on "
          f"this tree are byte-identical to the `jobSha256` their receipt recorded, "
          f"and the archive carries one build stamp.")
    print("So the solve below IS the solve those figures were rendered from. "
          "Checked, not assumed.")
    print()
