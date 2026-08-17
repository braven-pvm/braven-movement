$ErrorActionPreference = 'Stop'

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$previousIntegrationSetting = $env:BRAVEN_RUN_BLENDER_INTEGRATION
$env:BRAVEN_RUN_BLENDER_INTEGRATION = '1'
Push-Location $repositoryRoot
try {
    & python tests\test_blender_reference_config_integration.py -v
    if ($LASTEXITCODE -ne 0) {
        throw "Blender/MPFB integration test failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
    $env:BRAVEN_RUN_BLENDER_INTEGRATION = $previousIntegrationSetting
}
