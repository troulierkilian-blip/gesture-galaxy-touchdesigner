[CmdletBinding()]
param(
    [ValidateSet('GestureParticles.toe', 'build/Bootstrap.toe')]
    [string]$Project = 'GestureParticles.toe',
    [switch]$CheckOnly
)
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path $PSScriptRoot -Parent
$ProjectPath = Join-Path $ProjectRoot $Project
if (-not (Test-Path -LiteralPath $ProjectPath -PathType Leaf)) { throw "Project not found: $Project" }
if (-not (Test-Path -LiteralPath (Join-Path $ProjectRoot 'vendor/mediapipe-v0.6.0/toxes/MediaPipe.tox') -PathType Leaf)) {
    throw 'Run Setup-Dependencies.ps1 before starting the project.'
}
function Find-TouchDesigner {
    if ($env:TOUCHDESIGNER_EXE) {
        if (-not (Test-Path -LiteralPath $env:TOUCHDESIGNER_EXE -PathType Leaf)) {
            throw 'TOUCHDESIGNER_EXE does not point to an existing executable.'
        }
        return $env:TOUCHDESIGNER_EXE
    }
    $portable = Join-Path $ProjectRoot 'runtime/TouchDesigner/bin/TouchDesigner.exe'
    if (Test-Path -LiteralPath $portable -PathType Leaf) { return $portable }
    foreach ($base in @($env:ProgramFiles, ${env:ProgramFiles(x86)})) {
        if (-not $base) { continue }
        $derivative = Join-Path $base 'Derivative'
        if (-not (Test-Path -LiteralPath $derivative -PathType Container)) { continue }
        foreach ($folder in Get-ChildItem -LiteralPath $derivative -Directory | Where-Object Name -Like 'TouchDesigner*' | Sort-Object Name -Descending) {
            foreach ($relative in @('bin/TouchDesigner.exe', 'TouchDesigner.exe')) {
                $candidate = Join-Path $folder.FullName $relative
                if (Test-Path -LiteralPath $candidate -PathType Leaf) { return $candidate }
            }
        }
    }
    $command = Get-Command TouchDesigner.exe -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    throw 'TouchDesigner was not found. Install it from https://derivative.ca/download or set TOUCHDESIGNER_EXE.'
}
$Executable = Find-TouchDesigner
if ($CheckOnly) {
    Write-Host ('Executable: ' + $Executable)
    Write-Host ('Project: ' + $ProjectPath)
    return
}
Start-Process -FilePath $Executable -ArgumentList ('"' + $ProjectPath + '"') -WorkingDirectory $ProjectRoot
