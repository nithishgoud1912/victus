[CmdletBinding()]
param(
    [string]$Python = '',
    [string]$NodeDirectory = ''
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
if (-not $Python) { $Python = Join-Path $projectRoot '.local/package-venv/Scripts/python.exe' }
if (-not $NodeDirectory) { $NodeDirectory = Join-Path $projectRoot '.local/toolchains/node-v24.22.0-win-x64' }
if (-not (Test-Path -LiteralPath $Python)) { throw 'Prepare the pinned packaging environment first. See docs/release/README.md.' }
$savedPath = $env:PATH
try {
    $env:PATH = "$NodeDirectory;$savedPath"
    $env:VICTUS_PYTHON = $Python
    Push-Location $projectRoot
    try {
        & npm.cmd --prefix dashboard run build
        if ($LASTEXITCODE -ne 0) { throw 'Dashboard build failed' }
        $stageRoot = [IO.Path]::GetFullPath((Join-Path $projectRoot 'build/windows-staging'))
        $buildRoot = [IO.Path]::GetFullPath((Join-Path $projectRoot 'build')) + [IO.Path]::DirectorySeparatorChar
        if (-not $stageRoot.StartsWith($buildRoot, [StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe staging path' }
        if (Test-Path -LiteralPath $stageRoot) { Remove-Item -LiteralPath $stageRoot -Recurse -Force }
        New-Item -ItemType Directory -Path $stageRoot -Force | Out-Null
        Copy-Item -LiteralPath (Join-Path $projectRoot 'dashboard/dist') -Destination (Join-Path $stageRoot 'dashboard') -Recurse
        & $Python packaging/windows/make_icon.py
        if ($LASTEXITCODE -ne 0) { throw 'Icon creation failed' }
        & $Python -m PyInstaller --noconfirm --clean --distpath dist/windows --workpath build/pyinstaller packaging/windows/victus.spec
        if ($LASTEXITCODE -ne 0) { throw 'Folder bundle build failed' }
        & $Python packaging/windows/release_manifest.py (Join-Path $projectRoot 'dist/windows/Victus')
        if ($LASTEXITCODE -ne 0) { throw 'Release manifest failed' }
        Write-Output 'Folder bundle ready: dist/windows/Victus. Keep the entire folder together.'
    } finally { Pop-Location }
} finally {
    $env:PATH = $savedPath
    Remove-Item Env:VICTUS_PYTHON -ErrorAction SilentlyContinue
}
