[CmdletBinding()]
param(
    [string]$Output = 'out/manual',

    [string]$Config,

    [string]$BlenderExe = 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe',

    [int]$Every = 2,

    [string]$View = 'quarter',

    # Render only these movements. Every eligible drill by default.
    [string[]]$Movement,

    # Reuse the job files already in spikes/poc-output. The solve is the slow
    # part and it does not change unless the movement lane changes.
    [switch]$SkipJobs,

    # Reuse the stills already under -Output and only rebuild the page.
    [switch]$SkipRender
)

$ErrorActionPreference = 'Stop'
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$spikes = Join-Path $repositoryRoot 'spikes'
$jobDirectory = Join-Path $spikes 'poc-output'
$pixi = Join-Path $env:USERPROFILE '.pixi\bin\pixi.exe'
$outputPath = [System.IO.Path]::GetFullPath((Join-Path $repositoryRoot $Output))

if (-not (Test-Path $pixi)) {
    throw "pixi is not at $pixi. The solver lives in the pixi environment, not the repository .venv."
}
if (-not (Test-Path (Join-Path $spikes 'mhr-assets\assets\lod3.fbx'))) {
    throw @"
spikes/mhr-assets is missing or its junction is broken. It is 4.5 GB and git
ignores it, so a new worktree has no copy. Link it rather than downloading it
again:
  New-Item -ItemType Junction -Path "$spikes\mhr-assets" -Target "$repositoryRoot\.assets\mhr-assets"
"@
}

Push-Location $repositoryRoot
try {
    if (-not $SkipJobs) {
        Write-Host '== solving and exporting the jobs ==' -ForegroundColor Cyan
        $jobArguments = @('run', 'python', 'export_blender_job.py')
        if ($Movement) { $jobArguments += $Movement } else { $jobArguments += '--all' }
        $jobArguments += "--every=$Every"
        Push-Location $spikes
        try {
            & $pixi @jobArguments
            if ($LASTEXITCODE -ne 0) { throw "the job export failed with exit code $LASTEXITCODE" }
        }
        finally { Pop-Location }
    }

    $jobs = if ($Movement) {
        $Movement | ForEach-Object { Join-Path $jobDirectory "$_.job.json" }
    }
    else {
        Get-ChildItem (Join-Path $jobDirectory '*.job.json') | ForEach-Object { $_.FullName }
    }
    if (-not $jobs) { throw "no job files under $jobDirectory. Run without -SkipJobs." }
    foreach ($job in $jobs) {
        if (-not (Test-Path $job)) { throw "no job file at $job" }
    }

    if (-not $SkipRender) {
        Write-Host "== rendering $($jobs.Count) drills in one Blender session ==" -ForegroundColor Cyan
        Write-Host '   The athlete is built once. Expect about 17 seconds per phase view.'
        $renderArguments = @('-b', '--python-exit-code', '9', '-P',
                             (Join-Path $repositoryRoot 'blender_movement_render.py'), '--')
        foreach ($job in $jobs) { $renderArguments += @('--job', $job) }
        $renderArguments += @('--output', $outputPath)
        if ($Config) { $renderArguments += @('--config', (Resolve-Path $Config).Path) }

        & $BlenderExe @renderArguments
        if ($LASTEXITCODE -ne 0) { throw "the render failed with exit code $LASTEXITCODE" }
    }

    Write-Host '== assembling the manual page ==' -ForegroundColor Cyan
    Push-Location $spikes
    try {
        & $pixi run python export_manual_page.py --renders $outputPath --view $View
        if ($LASTEXITCODE -ne 0) { throw "the manual page build failed with exit code $LASTEXITCODE" }
    }
    finally { Pop-Location }

    Write-Host '== how near each hand came to the ball ==' -ForegroundColor Cyan
    & $pixi run python (Join-Path $PSScriptRoot 'report_clearance.py') $outputPath
}
finally {
    Pop-Location
}
