$victusRoot = Split-Path $PSScriptRoot -Parent
$victusVersion = (Get-Content -LiteralPath (Join-Path $victusRoot '.node-version') -Raw).Trim()
$victusNode = Join-Path $victusRoot ".local/toolchains/node-v$victusVersion-win-x64"
if (-not (Test-Path -LiteralPath (Join-Path $victusNode 'node.exe'))) {
    throw 'Run ./scripts/Install-Node.ps1 first.'
}
$env:PATH = "$victusNode;$env:PATH"
$env:npm_config_cache = Join-Path $victusRoot '.local/npm-cache'
