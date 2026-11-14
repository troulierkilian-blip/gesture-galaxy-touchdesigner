[CmdletBinding()]
param(
    [string]$CacheDirectory,
    [switch]$VerifyOnly
)
$ErrorActionPreference = 'Stop'
$ProjectRoot = [IO.Path]::GetFullPath($PSScriptRoot)
$Manifest = Get-Content -LiteralPath (Join-Path $ProjectRoot 'dependencies.json') -Raw | ConvertFrom-Json
if (-not $CacheDirectory) { $CacheDirectory = Join-Path $ProjectRoot '.dependency-cache' }

function Get-ProjectPath([string]$RelativePath) {
    $resolved = [IO.Path]::GetFullPath((Join-Path $ProjectRoot $RelativePath))
    $prefix = $ProjectRoot.TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
    if (-not $resolved.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Dependency path escapes project: $RelativePath"
    }
    return $resolved
}
function Test-Hash([string]$Path, [string]$Expected) {
    return ((Test-Path -LiteralPath $Path -PathType Leaf) -and
        ((Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash -ieq $Expected))
}
function Get-VerifiedAsset($Asset) {
    if ([IO.Path]::GetFileName($Asset.name) -ne $Asset.name) { throw 'Invalid cache filename' }
    New-Item -ItemType Directory -Path $CacheDirectory -Force | Out-Null
    $cached = Join-Path $CacheDirectory $Asset.name
    if (Test-Hash $cached $Asset.sha256) { return $cached }
    $partial = $cached + '.part'
    Write-Host ('Downloading ' + $Asset.name + ' from its pinned upstream version...')
    $curl = Get-Command curl.exe -ErrorAction SilentlyContinue
    if ($curl) {
        & $curl.Source --fail --show-error --location --retry 2 --connect-timeout 30 --max-time 1800 --continue-at - --output $partial $Asset.url
        if ($LASTEXITCODE -ne 0) { throw "Download failed: $($Asset.name)" }
    } else {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -UseBasicParsing -Uri $Asset.url -OutFile $partial -TimeoutSec 900
    }
    if (-not (Test-Hash $partial $Asset.sha256)) {
        throw "SHA-256 mismatch for $($Asset.name). The file was not installed."
    }
    Move-Item -LiteralPath $partial -Destination $cached -Force
    return $cached
}
function Test-InstalledRelease {
    foreach ($check in $Manifest.installed_checks.PSObject.Properties) {
        if (-not (Test-Hash (Get-ProjectPath $check.Name) $check.Value)) { return $false }
    }
    return $true
}
function Expand-VerifiedRelease([string]$Archive, [string]$Destination) {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [IO.Compression.ZipFile]::OpenRead($Archive)
    try {
        $base = [IO.Path]::GetFullPath($Destination).TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
        foreach ($entry in $zip.Entries) {
            $target = [IO.Path]::GetFullPath((Join-Path $Destination $entry.FullName))
            if (-not $target.StartsWith($base, [StringComparison]::OrdinalIgnoreCase)) {
                throw 'Archive entry escapes dependency directory'
            }
        }
    } finally { $zip.Dispose() }
    New-Item -ItemType Directory -Path $Destination -Force | Out-Null
    Expand-Archive -LiteralPath $Archive -DestinationPath $Destination -Force
}

foreach ($asset in $Manifest.assets) {
    $target = Get-ProjectPath $asset.target
    if ($asset.kind -eq 'release_zip') {
        $model = Get-ProjectPath 'vendor/mediapipe-v0.6.0/toxes/MediaPipe.tox'
        $expected = $Manifest.installed_checks.'vendor/mediapipe-v0.6.0/toxes/MediaPipe.tox'
        if (Test-Hash $model $expected) { continue }
        if ($VerifyOnly) { throw 'MediaPipe release is missing or has an unexpected hash' }
        Expand-VerifiedRelease (Get-VerifiedAsset $asset) $target
    } elseif ($asset.kind -eq 'file') {
        if (Test-Hash $target $asset.sha256) { continue }
        if ($VerifyOnly) { throw "Missing or altered dependency: $($asset.target)" }
        $cached = Get-VerifiedAsset $asset
        New-Item -ItemType Directory -Path (Split-Path $target -Parent) -Force | Out-Null
        Copy-Item -LiteralPath $cached -Destination $target -Force
    } else { throw 'Unknown dependency kind' }
}
if (-not (Test-InstalledRelease)) { throw 'Final component verification failed' }
Write-Host 'Dependencies verified: MediaPipe TouchDesigner v0.6.0 and exact-commit hand tracking sources.'
Write-Host 'Install/activate TouchDesigner separately, then run Start-GestureParticles.cmd.'
