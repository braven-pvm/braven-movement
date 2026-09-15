# Blender MCP, measured on this repository

Stage 1, item 4 of the character and animation lane. Written 2026-09-09 against
`f0b9616`.

The brief asks what Blender MCP is, whether one can drive this repository's
existing Blender render, and what it would buy over the script path that ships.
It says to measure it here rather than report what other people achieve. The
orchestrator added that if the answer is that it buys nothing, that is a result
and it gets published.

**It buys nothing on the path that makes the product, and the reason is
architectural rather than a missing feature.** The case is below with its
numbers.

## 1. What it is, in its own projects' words

**SEARCHED.** Several servers exist under this name. The widely used one is
`ahujasid/blender-mcp`; Blender's own lab has one; there are others.

They agree on the mechanism. A Blender ADDON opens a socket server inside a
running Blender. An MCP server outside talks to that socket. The assistant then
calls tools that create objects, assign materials, render, export, and execute
arbitrary Python inside that Blender.

Two requirements matter here, and both are quoted rather than paraphrased:

- **Blender must be running with a GUI**, with the addon enabled and its server
  started from the sidebar, before any tool call can do anything.
- **It runs arbitrary Python.** `ahujasid/blender-mcp` says of its
  `execute_blender_code` tool: "allows running arbitrary Python code in Blender,
  which can be powerful but potentially dangerous. Use with caution in
  production environments. **ALWAYS save your work before using it.**" Blender's
  own lab page is quoted by aggregators as warning that the server "will execute
  LLM generated code in Blender without any guards in place".

## 2. Can it drive this render path? No, and not for a small reason

**MEASURED on this machine.**

- **No Blender MCP tool is available in this session.** A tool search for a
  Blender server returns nothing.
- **No MCP addon is installed.** The only Blender extension present is `mpfb`.

Those two are circumstance and could be changed in an afternoon. **The reason it
does not fit is not circumstance.**

**This path is headless by construction.** Every render in this repository is
`blender -b`, background, no window, driven by `-P blender_movement_render.py`
and a job file. Blender MCP needs an interactive Blender with a person's
sidebar. The two do not meet: a socket server inside a GUI session cannot drive
a `-b` process that starts, renders and exits.

An MCP server could of course start `blender -b` for us. **That is what a shell
already does**, and it is what `scripts/render-reference.ps1` and the commands
in `docs/HANDOFF_RENDERING.md` already are.

## 3. What the script path costs, measured rather than quoted

The baseline any alternative has to beat, measured on this machine at
`5d0406e`, on `netball_chest_pass`:

| what | measurement | method |
|---|---|---|
| bare Blender start, no script | 1319 ms, 1217 ms | `blender -b --python-expr "pass"`, twice |
| whole process, athlete built, nothing rendered | 5749, 5978, 5752 ms | `--phase no_such_phase`, three times |
| **so the athlete build and scene setup** | **about 4.5 s** | the difference of the two medians |
| one rendered view, 1080 x 1350 | 16.55 s, 16.43 s, 15.23 s | Blender's own `Time:` lines, one run of three views |

**So one figure, from a cold start, is about 22 seconds**: 5.75 for the process
and the athlete, plus 16.5 for the view. Three views of one phase is about 54
seconds, which is what the wall clock showed.

**AND ONE NUMBER IN `docs/HANDOFF_RENDERING.md` IS STALE.** That file says
"building the athlete costs about two minutes and a phase view costs about
seventeen seconds". **The seventeen seconds is right** and my three views
measured 15.2 to 16.6. **The two minutes is not**: the build measures about 4.5
seconds here, which is a factor of about 26.

The sentence is the argument for batching drills into one Blender session. **The
argument survives on the per-view cost and not on the build cost.** Batching 8
drills into one session saves 7 of the 8 startups, which is about 40 seconds at
the measured cost, and not the 14 minutes the stated figure implies.

**I have not edited that file.** It is the rendering lane's, the figure may have
been true when it was written or may be measuring something else, and a stale
number is refreshed by the lane that owns it. It is reported to the orchestrator
instead.

## 4. What it would cost this repository, beyond the time

Two of this repository's own architecture rules are the obstacle, and neither is
negotiable by this lane.

**`docs/ARCHITECTURE.md` rule 6.** Athlete phenotype, readiness, expression,
pose, camera, material colours, ball construction, studio colours and lighting
"remain versioned configuration or deterministic generator code; they are not
manual `.blend` edits". **An assistant driving a live Blender is a manual edit
by another name.** The fact that a machine types it does not make it versioned.

**`docs/ARCHITECTURE.md` rule 7, and the build stamp under it.** A receipt
records the configuration hash, the asset hashes and the build. Every render
receipt in this repository names a commit and says whether the tree was clean;
I watched it correctly refuse to claim reproducibility twice today, during two
experiments that dirtied the tree. **An interactive session has no commit and no
configuration to hash.** A picture made that way cannot carry a receipt that
means anything, and a picture without a receipt cannot reach a coach under P1,
where a coach's marks are scored against the build she graded.

**And the arbitrary-code warning lands harder here than in a hobby scene.** This
repository's assets live at `.assets`, are not in git, and one of them is
irreplaceable enough that its own documentation says it was one worktree event
from not existing.

## 5. Where it could earn its place, and why even that is weak here

The honest case for it is EXPLORATION rather than production: trying asset
combinations quickly, by eye, without writing a script.

Item 3 leaves exactly that work open. Twenty-two unused skins, nine unused hair
assets, five unused shoe sets.

**But the measurement above weakens even that case.** One option, rendered from
a cold start, is about 21 seconds, and swapping the asset is one string. The
experiment in item 3 section 3 swapped a kit asset, rendered three views and
restored the tree, and the whole thing was one script and about a minute.
**A conversation with a live Blender would not obviously be faster, and its
result would not be reproducible.**

## 6. The verdict, and what would change it

**Publishing the negative: Blender MCP buys nothing on the path that makes the
product here.** It cannot drive a headless render, and adopting it would put a
figure in front of a coach that no receipt can trace to a build.

Three things would change that answer, and none of them is true today:

1. **A server that drives `blender -b` with a job file** rather than a live
   session. That is not what these servers are; it is what a shell is.
2. **A figure path that does not need a receipt.** There is not one. Every
   figure a coach sees is graded under P1 against the build it came from.
3. **An exploration cost that the script path cannot meet.** At 21 seconds an
   option, it can.

## 7. What I did not do

- **I did not install it.** Installing an addon that executes arbitrary
  LLM-written Python, on the machine that holds the only copy of the assets, is
  not a thing to do to answer a research question.
- **I could not read the two blender.org pages.** Both
  `https://www.blender.org/lab/mcp-server/` and
  `https://projects.blender.org/lab/blender_mcp` returned HTTP 403 to my fetch.
  What is attributed to Blender's own lab above is quoted from an aggregator
  quoting it, and it is weaker evidence than the `ahujasid` README, which I read
  directly. If this decision ever turns on the official server's exact
  behaviour, somebody with a browser must read those two pages.
- **I did not measure a GPU or a different machine.** Every number in section 3
  is this machine at this commit, and a hosted runner is a different machine.

## Sources

- [ahujasid/blender-mcp on GitHub](https://github.com/ahujasid/blender-mcp)
- [MCP Server — Blender](https://www.blender.org/lab/mcp-server/) (403 to my fetch)
- [lab/blender_mcp — Blender Projects](https://projects.blender.org/lab/blender_mcp) (403 to my fetch)
- [BlenderMCP MCP Server — Awesome MCP Servers](https://mcpservers.org/servers/blender-mcp)
