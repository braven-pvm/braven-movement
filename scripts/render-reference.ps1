[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Output,

    [string]$Config,

    [string]$BlenderExe = 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe',

    [switch]$ReferenceCompared
)

$ErrorActionPreference = 'Stop'
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$generator = Join-Path $repositoryRoot 'blender_mpfb_reference_catch.py'
if ([string]::IsNullOrWhiteSpace($Config)) {
    $Config = Join-Path $repositoryRoot 'config\reference_catch.v1.json'
}

$generatorArguments = @(
    '-b',
    '--python-exit-code', '9',
    '-P', $generator,
    '--',
    '--config', (Resolve-Path $Config).Path,
    '--output', [System.IO.Path]::GetFullPath($Output)
)
if ($ReferenceCompared) {
    $generatorArguments += '--reference-compared'
}

& $BlenderExe @generatorArguments
if ($LASTEXITCODE -ne 0) {
    throw "Blender generator failed with exit code $LASTEXITCODE"
}
