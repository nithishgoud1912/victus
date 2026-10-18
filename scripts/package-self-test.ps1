[CmdletBinding()]
param(
    [string]$Bundle = '',
    [string]$OutputDirectory = ''
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
if (-not $Bundle) { $Bundle = Join-Path $projectRoot 'dist/windows/Victus' }
$Bundle = (Resolve-Path -LiteralPath $Bundle).Path
if (-not $OutputDirectory) { $OutputDirectory = Join-Path $projectRoot ('.local/package-self-test-' + [guid]::NewGuid().ToString('N')) }
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Choose a new test output directory.' }
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
$OutputDirectory = (Resolve-Path -LiteralPath $OutputDirectory).Path
$executable = Join-Path $Bundle 'Victus.exe'
$testData = Join-Path $OutputDirectory 'data'
$saved = @{}
$names = @('VICTUS_DATA_DIR','VICTUS_API_TOKEN','VICTUS_VOICE_MODEL_PATH','VICTUS_WAKE_MANIFEST_PATH','VICTUS_MCP_NOTES','VICTUS_CLOUD_MODEL','VICTUS_CLOUD_UPSTREAM','VICTUS_EMERGENCY_HOTKEY','VICTUS_DASHBOARD_DEV_ORIGIN','VICTUS_COMMAND_MODEL','VICTUS_COMMAND_MODEL_DIGEST')
foreach ($name in $names) { $saved[$name] = [Environment]::GetEnvironmentVariable($name, 'Process'); [Environment]::SetEnvironmentVariable($name, $null, 'Process') }
$server = $null
$checks = [ordered]@{}
$report = [ordered]@{ version=''; passed=$false; qualification='same-account-laptop-only'; checks=$checks; fresh_standard_account_tested=$false; gpu_browser_microphone_tested=$false; source_sha256=$null; bundle_manifest_sha256=$null }

function Assert-Check([string]$Name, [bool]$Condition) {
    $checks[$Name] = $Condition
    if (-not $Condition) { throw "Check failed: $Name" }
}
function Invoke-CLI([string[]]$Arguments, [bool]$Success = $true) {
    $result = & $executable @Arguments 2>&1
    $code = $LASTEXITCODE
    if ($Success -and $code -ne 0) { throw 'Packaged command failed; inspect local private output if needed.' }
    if (-not $Success -and $code -eq 0) { throw 'Packaged maintenance unexpectedly succeeded.' }
    return ($result -join "`n")
}
function Start-TestService {
    return Start-Process -FilePath $executable -ArgumentList @('serve') -WorkingDirectory $Bundle -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $OutputDirectory 'service.stdout.log') -RedirectStandardError (Join-Path $OutputDirectory 'service.stderr.log')
}
function Wait-Service {
    for ($i=0; $i -lt 100; $i++) {
        if ($server.HasExited) { throw 'Packaged service exited before readiness.' }
        try { $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8765/api/health' -Headers $headers -TimeoutSec 1; return $health } catch { Start-Sleep -Milliseconds 150 }
    }
    throw 'Packaged service readiness deadline exceeded.'
}
try {
    # Do not stop or reuse an unrelated listener on the product port.
    $occupied = Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue
    if ($occupied) { throw 'Port 8765 is already occupied. Stop your own service before this test.' }
    $env:VICTUS_DATA_DIR = $testData
    $env:VICTUS_API_TOKEN = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
    $headers = @{ Authorization = 'Bearer ' + $env:VICTUS_API_TOKEN }
    $manifest = Get-Content -LiteralPath (Join-Path $Bundle 'release-manifest.json') -Raw | ConvertFrom-Json
    $report.bundle_manifest_sha256 = (Get-FileHash -LiteralPath (Join-Path $Bundle 'release-manifest.json') -Algorithm SHA256).Hash.ToLowerInvariant()
    $report.source_sha256 = $manifest.source_sha256
    $bundlePrefix = [IO.Path]::GetFullPath($Bundle) + [IO.Path]::DirectorySeparatorChar
    $validHashes = $manifest.files.Count -gt 0 -and $manifest.files.Count -lt 20000
    foreach ($file in $manifest.files) {
        $candidate = [IO.Path]::GetFullPath((Join-Path $Bundle $file.path))
        if (-not $candidate.StartsWith($bundlePrefix, [StringComparison]::OrdinalIgnoreCase)) { $validHashes=$false; break }
        if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) { $validHashes=$false; break }
        if ((Get-FileHash -LiteralPath $candidate -Algorithm SHA256).Hash.ToLower() -ne $file.sha256) { $validHashes=$false; break }
    }
    Assert-Check 'bundle_checksums' $validHashes
    Assert-Check 'windows_version_metadata' ((Get-Item -LiteralPath $executable).VersionInfo.FileVersion -eq '0.1.0.0')
    $report.version = (Invoke-CLI -Arguments @('version')).Trim()
    Assert-Check 'entry_version' ($report.version -eq '0.1.0')
    $doctor = (Invoke-CLI -Arguments @('doctor')) | ConvertFrom-Json
    Assert-Check 'dashboard_staged' ($doctor.dashboard -eq 'installed')
    Assert-Check 'data_root_selection' ([IO.Path]::GetFullPath($doctor.data_dir) -eq [IO.Path]::GetFullPath($testData))
    Assert-Check 'missing_dependency_messages' ($doctor.voice -eq 'local_model_not_configured_or_missing' -and $doctor.voice_message -and $doctor.browser_message -and $doctor.ollama_message)
    Assert-Check 'no_autostart_or_listening' ($doctor.autostart -eq 'not_installed' -and $doctor.wake -eq 'off_until_explicitly_enabled')
    $server = Start-TestService
    $health = Wait-Service
    try { Invoke-RestMethod -Uri 'http://127.0.0.1:8765/api/health' -TimeoutSec 2 | Out-Null; $unauthorized=$false }
    catch { $unauthorized = [int]$_.Exception.Response.StatusCode -eq 401 }
    Assert-Check 'api_auth_required' $unauthorized
    Assert-Check 'api_authorized' ($health.status -eq 'ok')
    $html = Invoke-WebRequest -Uri 'http://127.0.0.1:8765/' -TimeoutSec 3
    Assert-Check 'dashboard_http' ($html.StatusCode -eq 200 -and $html.Content.Contains('id="root"'))
    $voice = Invoke-RestMethod -Uri 'http://127.0.0.1:8765/api/voice' -Headers $headers
    Assert-Check 'voice_disabled_without_asset' (-not $voice.enabled -and -not $voice.wake_listening)
    $second = Start-Process -FilePath $executable -ArgumentList @('migrate') -WorkingDirectory $Bundle -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $OutputDirectory 'second.stdout.log') -RedirectStandardError (Join-Path $OutputDirectory 'second.stderr.log')
    if (-not $second.WaitForExit(10000)) { $second.Kill(); throw 'Second instance did not exit' }
    Assert-Check 'instance_lock' ($second.ExitCode -ne 0)
    # Exercise a frozen spawned worker. Resource pressure is recorded honestly.
    $payload = @{tool='fs.create_note';arguments=@{filename='package-proof.txt';text='Package self-test fixture'}} | ConvertTo-Json -Depth 4
    $queued = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8765/api/tasks' -Headers $headers -ContentType 'application/json' -Body $payload
    for ($i=0; $i -lt 100; $i++) {
        $task = Invoke-RestMethod -Uri ('http://127.0.0.1:8765/api/tasks/' + $queued.task_id) -Headers $headers
        if ($task.status -notin @('queued','prepared','running')) { break }
        Start-Sleep -Milliseconds 100
    }
    Assert-Check 'frozen_worker_verified' ($task.status -eq 'succeeded' -and $task.verified)
    $commandHeaders = @{Authorization=$headers.Authorization; 'X-Client-Request-ID'='package-command'}
    $commandBody = @{text='Create a note command-proof.txt containing "Command package proof"'} | ConvertTo-Json
    $command = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8765/api/commands' -Headers $commandHeaders -ContentType 'application/json' -Body $commandBody
    Assert-Check 'frozen_command_admitted' ($command.state -eq 'submitted')
    for ($i=0; $i -lt 200; $i++) {
        $commandTask = Invoke-RestMethod -Uri ('http://127.0.0.1:8765/api/tasks/' + $command.task_id) -Headers $headers
        if ($commandTask.status -notin @('queued','prepared','running','waiting_for_review')) { break }
        Start-Sleep -Milliseconds 100
    }
    Assert-Check 'frozen_command_graph_verified' ($commandTask.verified -and (Get-Content -LiteralPath (Join-Path $testData 'workspace/command-proof.txt') -Raw) -eq 'Command package proof')
    $replay = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8765/api/commands' -Headers $commandHeaders -ContentType 'application/json' -Body $commandBody
    Assert-Check 'frozen_command_replay' ($replay.task_id -eq $command.task_id)
    $commandHeaders['X-Client-Request-ID'] = 'package-clarification'
    $clarification = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8765/api/commands' -Headers $commandHeaders -ContentType 'application/json' -Body '{"text":"Create a note"}'
    $snapshot = Invoke-RestMethod -Uri ('http://127.0.0.1:8765/api/commands/' + $clarification.command_id) -Headers $headers
    Assert-Check 'frozen_clarification_read_only' ($snapshot.state -eq 'clarification' -and $snapshot.missing.Count -eq 2)
    Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8765/api/stop' -Headers $headers | Out-Null
    $stopped = Invoke-RestMethod -Uri 'http://127.0.0.1:8765/api/health' -Headers $headers
    Assert-Check 'stop_then_maintenance' $stopped.stopped
    $server.Kill(); $server.WaitForExit(); $server = $null
    # Update rehearsal: offline backup, idempotent migration, restart new entry.
    $backup = Join-Path $OutputDirectory 'pre-update-backup'
    Invoke-CLI -Arguments @('backup','--destination',$backup) | Out-Null
    $migration = (Invoke-CLI -Arguments @('migrate')) | ConvertFrom-Json
    Assert-Check 'schema_migration' ($migration.schema -eq 8)
    $server = Start-TestService
    $null = Wait-Service
    Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8765/api/stop' -Headers $headers | Out-Null
    $server.Kill(); $server.WaitForExit(); $server = $null
    $restored = Join-Path $OutputDirectory 'rollback-data'
    Invoke-CLI -Arguments @('restore','--source',$backup,'--destination',$restored) | Out-Null
    Assert-Check 'backup_and_restore' (Test-Path -LiteralPath (Join-Path $restored 'restore-review.json'))
    $env:VICTUS_DATA_DIR = $restored
    $server = Start-TestService
    $null = Wait-Service
    Assert-Check 'rollback_restart' ((Get-Content -LiteralPath (Join-Path $restored 'workspace/package-proof.txt') -Raw) -eq 'Package self-test fixture')
    Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8765/api/stop' -Headers $headers | Out-Null
    $report.passed = $true
} catch {
    # Error class only: raw provider/server paths and tokens stay out of exports.
    $report.failure = 'PACKAGE_SELF_TEST_FAILED'
    Write-Warning 'Package self-test failed; review the check names and private local service logs.'
} finally {
    if ($server -and -not $server.HasExited) { $server.Kill(); $server.WaitForExit() }
    foreach ($name in $names) { [Environment]::SetEnvironmentVariable($name, $saved[$name], 'Process') }
    $report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $OutputDirectory 'report.json')
}
if (-not $report.passed) { exit 1 }
Write-Output 'Package self-test passed. Fresh-account and target-device qualification remain separate.'
