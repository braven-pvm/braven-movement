param(
    [int]$Port = 5397,
    [string]$AthleteOutput = $env:BRAVEN_ATHLETE_OUTPUT,
    [string]$TacticsPath = $env:BRAVEN_TACTICS_PATH,
    [switch]$Rebuild,
    [switch]$NoBrowser
)
$ErrorActionPreference = 'Stop'
$studioViewer = Join-Path $PSScriptRoot 'viewer'
$studioDist = Join-Path $studioViewer 'dist'
$studioReceiptPath = Join-Path $studioDist 'studio-build.json'
$studioInputsPath = Join-Path $studioViewer '.local\build-inputs.json'
$studioUrl = "http://127.0.0.1:$Port/"
if ($Port -lt 1024 -or $Port -gt 65535) { throw 'Choose a port between 1024 and 65535.' }

if ($Rebuild -or -not (Test-Path -LiteralPath $studioReceiptPath)) {
    if (Test-Path -LiteralPath $studioInputsPath) {
        $studioInputs = Get-Content -LiteralPath $studioInputsPath -Raw | ConvertFrom-Json
        if (-not $AthleteOutput) { $AthleteOutput = $studioInputs.athleteOutput }
        if (-not $TacticsPath) { $TacticsPath = $studioInputs.tacticsPath }
    }
    if (-not $AthleteOutput) { $AthleteOutput = 'E:\cloud services\OneDrive - About IT Group (Pty) Ltd\Documents\ChatGPT\Braven Movement\Netball Athlete' }
    if (-not $TacticsPath) { $TacticsPath = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\braven-tactics-netball-athlete')) }
    if (-not (Test-Path -LiteralPath (Join-Path $AthleteOutput 'netball-athlete.glb'))) { throw 'Supply -AthleteOutput with the exported athlete directory.' }
    if (-not (Test-Path -LiteralPath (Join-Path $TacticsPath 'src\engine\skinned.ts'))) { throw 'Supply -TacticsPath with the compatible Tactics checkout.' }
    $env:BRAVEN_ATHLETE_OUTPUT = $AthleteOutput
    $env:BRAVEN_TACTICS_PATH = $TacticsPath
    Push-Location $studioViewer
    try {
        if (-not (Test-Path -LiteralPath 'node_modules\vite')) { & npm.cmd ci; if ($LASTEXITCODE -ne 0) { throw 'Studio dependency installation failed.' } }
        & npm.cmd run build
        if ($LASTEXITCODE -ne 0) { throw 'Studio build failed.' }
        New-Item -ItemType Directory -Force -Path (Split-Path $studioInputsPath) | Out-Null
        @{ athleteOutput = [IO.Path]::GetFullPath($AthleteOutput); tacticsPath = [IO.Path]::GetFullPath($TacticsPath) } | ConvertTo-Json | Set-Content -LiteralPath $studioInputsPath
    } finally { Pop-Location }
}
$studioExpected = Get-Content -LiteralPath $studioReceiptPath -Raw | ConvertFrom-Json
function Read-StudioBuild {
    try { return Invoke-RestMethod -Uri ($studioUrl + 'studio-build.json') -TimeoutSec 2 } catch { return $null }
}
$studioExisting = Read-StudioBuild
if ($studioExisting -and ($studioExisting.app -ne 'braven-studio' -or $studioExisting.buildId -ne $studioExpected.buildId)) {
    throw "Port $Port serves a different build. Choose another -Port."
}
if (-not $studioExisting) {
    $studioLogs = Join-Path $studioViewer '.local'
    New-Item -ItemType Directory -Force -Path $studioLogs | Out-Null
    $studioPython = (Get-Command python -ErrorAction Stop).Source
    $studioArgs = @(('"{0}"' -f (Join-Path $PSScriptRoot 'serve.py')), '--root', ('"{0}"' -f $studioDist), '--port', "$Port")
    $studioProcess = Start-Process -FilePath $studioPython -ArgumentList $studioArgs -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $studioLogs 'server.log') -RedirectStandardError (Join-Path $studioLogs 'server-error.log')
    for ($studioAttempt = 0; $studioAttempt -lt 30; $studioAttempt++) {
        if ((Read-StudioBuild).buildId -eq $studioExpected.buildId) { break }
        if ($studioProcess.HasExited) { throw 'Studio could not start. Check viewer/.local/server-error.log or choose a different port.' }
        Start-Sleep -Milliseconds 200
    }
    if ((Read-StudioBuild).buildId -ne $studioExpected.buildId) { throw 'Studio did not become ready.' }
    Set-Content -LiteralPath (Join-Path $studioLogs 'server.pid') -Value $studioProcess.Id
}
Write-Output "Braven Studio: $studioUrl"
Write-Output "Build: $($studioExpected.buildId)"
if (-not $NoBrowser) { Start-Process $studioUrl }
