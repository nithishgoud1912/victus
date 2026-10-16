$ErrorActionPreference = 'Stop'
$victusRoot = Split-Path $PSScriptRoot -Parent
$victusVersion = (Get-Content -LiteralPath (Join-Path $victusRoot '.node-version') -Raw).Trim()
if ($victusVersion -notmatch '^24\.\d+\.\d+$') { throw 'Expected the pinned Node 24 LTS version.' }
$victusName = "node-v$victusVersion-win-x64"
$victusTools = Join-Path $victusRoot '.local/toolchains'
$victusInstall = Join-Path $victusTools $victusName
if (Test-Path -LiteralPath (Join-Path $victusInstall 'node.exe')) {
    & (Join-Path $victusInstall 'node.exe') --version
    exit $LASTEXITCODE
}
New-Item -ItemType Directory -Force -Path $victusTools | Out-Null
$victusArchive = Join-Path $victusTools "$victusName.zip"
$victusBase = "https://nodejs.org/dist/v$victusVersion"
$victusChecksums = (Invoke-WebRequest -Uri "$victusBase/SHASUMS256.txt").Content
$victusLine = $victusChecksums -split "`n" | Where-Object { $_.Trim().EndsWith(" $victusName.zip") }
if (@($victusLine).Count -ne 1) { throw 'Missing official Node archive checksum.' }
$victusExpected = ($victusLine.Trim() -split '\s+')[0]
Invoke-WebRequest -Uri "$victusBase/$victusName.zip" -OutFile $victusArchive
$victusActual = (Get-FileHash -LiteralPath $victusArchive -Algorithm SHA256).Hash
if ($victusActual.ToLowerInvariant() -ne $victusExpected) { throw 'Node archive checksum mismatch.' }
Expand-Archive -LiteralPath $victusArchive -DestinationPath $victusTools
& (Join-Path $victusInstall 'node.exe') --version
if ($LASTEXITCODE -ne 0) { throw 'Node verification failed.' }
Write-Output "Installed project-local Node LTS in $victusInstall"
