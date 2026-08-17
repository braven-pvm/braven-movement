$ErrorActionPreference = 'Stop'

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Push-Location $repositoryRoot
try {
    & python -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) {
        throw "Host-side tests failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}
