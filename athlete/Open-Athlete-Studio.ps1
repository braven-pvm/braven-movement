param([int]$Port = 5393, [switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$taskUrl = "http://127.0.0.1:$Port/"
$taskManifestPath = Join-Path $PSScriptRoot 'studio\athlete-assets\manifest.json'
if (-not (Test-Path -LiteralPath $taskManifestPath)) { throw 'The packaged studio folder is missing beside this launcher.' }
$taskManifest = Get-Content -LiteralPath $taskManifestPath -Raw | ConvertFrom-Json
$taskHash = $taskManifest.files.'netball-athlete.glb'.sha256

function Read-ServedAthleteHash {
    try {
        $taskReply = Invoke-RestMethod -Uri ($taskUrl + 'athlete-assets/manifest.json') -TimeoutSec 2
        return $taskReply.files.'netball-athlete.glb'.sha256
    } catch { return $null }
}

$taskExisting = Read-ServedAthleteHash
if ($taskExisting -and $taskExisting -ne $taskHash) { throw "Port $Port serves a different athlete build. Choose another -Port." }
if (-not $taskExisting) {
    $taskPython = (Get-Command python -ErrorAction Stop).Source
    $taskProcess = Start-Process -FilePath $taskPython -ArgumentList @('serve.py', '--root', 'studio', '--port', "$Port") -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $PSScriptRoot 'studio-server.log') -RedirectStandardError (Join-Path $PSScriptRoot 'studio-server-error.log')
    for ($taskAttempt = 0; $taskAttempt -lt 20; $taskAttempt++) {
        if ((Read-ServedAthleteHash) -eq $taskHash) { break }
        if ($taskProcess.HasExited) { throw 'The studio server exited. Check studio-server-error.log or choose another -Port.' }
        Start-Sleep -Milliseconds 250
    }
    if ((Read-ServedAthleteHash) -ne $taskHash) { throw 'The studio did not become ready.' }
    Set-Content -LiteralPath (Join-Path $PSScriptRoot 'studio-server.pid') -Value $taskProcess.Id
}
Write-Output "Athlete studio is ready: $taskUrl"
if (-not $NoBrowser) { Start-Process $taskUrl }
