[CmdletBinding()]
param(
    [string]$Python = '',
    [string]$NodeDirectory = '',
    [string]$OutputDirectory = '',
    [string]$WorkDirectory = '',
    [string]$SourceManifest = ''
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
if (-not $Python) { $Python = Join-Path $projectRoot '.local/package-venv/Scripts/python.exe' }
if (-not $NodeDirectory) { $NodeDirectory = Join-Path $projectRoot '.local/toolchains/node-v24.22.0-win-x64' }
if (-not (Test-Path -LiteralPath $Python)) { throw 'Prepare the pinned packaging environment first. See docs/release/README.md.' }
$savedPath = $env:PATH
$savedStage = $env:VICTUS_BUILD_STAGE
$savedSource = $env:VICTUS_BUILD_SOURCE_MANIFEST
$savedPython = $env:VICTUS_PYTHON
if (-not $OutputDirectory) { $OutputDirectory = Join-Path $projectRoot 'dist/windows' }
if (-not $WorkDirectory) { $WorkDirectory = Join-Path $projectRoot ('.local/windows-build-' + [guid]::NewGuid().ToString('N')) }
if ((Test-Path -LiteralPath $OutputDirectory) -or (Test-Path -LiteralPath $WorkDirectory)) { throw 'Choose new build and output directories; existing packages are preserved.' }
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
$WorkDirectory = [IO.Path]::GetFullPath($WorkDirectory)
try {
    $env:PATH = "$NodeDirectory;$savedPath"
    $env:VICTUS_PYTHON = $Python
    Push-Location $projectRoot
    try {
        & npm.cmd --prefix dashboard run build
        if ($LASTEXITCODE -ne 0) { throw 'Dashboard build failed' }
        $stageRoot = Join-Path $WorkDirectory 'staging'
        $env:VICTUS_BUILD_STAGE = $stageRoot
        $env:VICTUS_BUILD_SOURCE_MANIFEST = if ($SourceManifest) { (Resolve-Path -LiteralPath $SourceManifest).Path } else { '' }
        New-Item -ItemType Directory -Path $stageRoot -Force | Out-Null
        Copy-Item -LiteralPath (Join-Path $projectRoot 'dashboard/dist') -Destination (Join-Path $stageRoot 'dashboard') -Recurse
        & $Python packaging/windows/make_icon.py
        if ($LASTEXITCODE -ne 0) { throw 'Icon creation failed' }
        & $Python -m PyInstaller --noconfirm --clean --distpath $OutputDirectory --workpath (Join-Path $WorkDirectory 'pyinstaller') packaging/windows/victus.spec
        if ($LASTEXITCODE -ne 0) { throw 'Folder bundle build failed' }
        & $Python packaging/windows/release_manifest.py (Join-Path $OutputDirectory 'Victus')
        if ($LASTEXITCODE -ne 0) { throw 'Release manifest failed' }
        Write-Output "Folder bundle ready: $OutputDirectory/Victus. Keep the entire folder together."
    } finally { Pop-Location }
} finally {
    $env:PATH = $savedPath
    $env:VICTUS_PYTHON = $savedPython
    $env:VICTUS_BUILD_STAGE = $savedStage
    $env:VICTUS_BUILD_SOURCE_MANIFEST = $savedSource
}
