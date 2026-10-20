[CmdletBinding()]
param([Parameter(Mandatory)][string]$PriorBundle,
      [Parameter(Mandatory)][string]$CandidateBundle,
      [Parameter(Mandatory)][string]$OutputDirectory)
$ErrorActionPreference='Stop'
$PriorBundle=(Resolve-Path -LiteralPath $PriorBundle).Path
$CandidateBundle=(Resolve-Path -LiteralPath $CandidateBundle).Path
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Choose a fresh output directory.' }
New-Item -ItemType Directory -Path $OutputDirectory | Out-Null
$OutputDirectory=(Resolve-Path -LiteralPath $OutputDirectory).Path
$old=Join-Path $PriorBundle 'Victus.exe'
$new=Join-Path $CandidateBundle 'Victus.exe'
$server=$null
$checks=[ordered]@{}
$report=[ordered]@{passed=$false;qualification='isolated-prior-artifact-pair';checks=$checks;fresh_standard_account_tested=$false;formal_cross_version_release_qualified=$false;graceful_server_shutdown_observed=$false;forced_server_terminations=0;cleanup_complete=$false}
$saved=@{}
$names=@('VICTUS_DATA_DIR','VICTUS_API_TOKEN','VICTUS_VOICE_MODEL_PATH','VICTUS_WAKE_MANIFEST_PATH','VICTUS_COMMAND_MODEL','VICTUS_COMMAND_MODEL_DIGEST','VICTUS_MCP_NOTES','VICTUS_CLOUD_MODEL','VICTUS_CLOUD_UPSTREAM','VICTUS_EMERGENCY_HOTKEY','VICTUS_DASHBOARD_DEV_ORIGIN')
foreach($name in $names){$saved[$name]=[Environment]::GetEnvironmentVariable($name,'Process');[Environment]::SetEnvironmentVariable($name,$null,'Process')}
function Check([string]$name,[bool]$ok){$checks[$name]=$ok;if(-not $ok){throw "Failed: $name"}}
function Invoke-VictusOffline([string]$exe,[string[]]$parameters){$value=& $exe @parameters 2>&1;if($LASTEXITCODE -ne 0){throw 'Offline command failed'};return ($value -join "`n")}
function Launch([string]$exe,[string]$label){
    $script:server=Start-Process -FilePath $exe -ArgumentList @('serve') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $OutputDirectory ($label+'.stdout.log')) -RedirectStandardError (Join-Path $OutputDirectory ($label+'.stderr.log'))
    for($i=0;$i -lt 100;$i++){
        if($server.HasExited){throw 'Service exited'}
        try{$null=Invoke-RestMethod -Uri 'http://127.0.0.1:8765/api/health' -Headers $headers -TimeoutSec 1;return}catch{Start-Sleep -Milliseconds 150}
    }
    throw 'Service readiness deadline'
}
function Stop-Owned{
    Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8765/api/stop' -Headers $headers | Out-Null
    $report.forced_server_terminations++
    $server.Kill();if(-not $server.WaitForExit(10000)){throw 'Owned cleanup deadline'};$script:server=$null
}
function Wait-Task([string]$id){
    for($i=0;$i -lt 250;$i++){
        $task=Invoke-RestMethod -Uri ('http://127.0.0.1:8765/api/tasks/'+$id) -Headers $headers
        if($task.status -notin @('queued','prepared','running','waiting_for_review')){return $task}
        Start-Sleep -Milliseconds 100
    }
    throw 'Task deadline'
}
try{
    if(Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue){throw 'Port already occupied'}
    $priorHash=(Get-FileHash -LiteralPath (Join-Path $PriorBundle 'release-manifest.json') -Algorithm SHA256).Hash
    $candidateHash=(Get-FileHash -LiteralPath (Join-Path $CandidateBundle 'release-manifest.json') -Algorithm SHA256).Hash
    Check 'distinct_prior_and_candidate_artifacts' ($priorHash -ne $candidateHash)
    $report.prior_manifest_sha256=$priorHash.ToLower();$report.candidate_manifest_sha256=$candidateHash.ToLower()
    $report.prior_executable_sha256=(Get-FileHash -LiteralPath $old -Algorithm SHA256).Hash.ToLower()
    $report.candidate_executable_sha256=(Get-FileHash -LiteralPath $new -Algorithm SHA256).Hash.ToLower()
    $integrity=(Invoke-VictusOffline $new @('verify-bundle'))|ConvertFrom-Json
    Check 'candidate_exact_inventory' ($integrity.integrity_verified -and $integrity.bundle_manifest_sha256 -eq $report.candidate_manifest_sha256)
    $priorIntegrity=(Invoke-VictusOffline $new @('verify-bundle','--source',$PriorBundle))|ConvertFrom-Json
    Check 'prior_exact_inventory' ($priorIntegrity.integrity_verified -and $priorIntegrity.bundle_manifest_sha256 -eq $report.prior_manifest_sha256)
    $report.prior_version=(Invoke-VictusOffline $old @('version')).Trim();$report.candidate_version=(Invoke-VictusOffline $new @('version')).Trim()
    $report.same_product_version=$report.prior_version -eq $report.candidate_version
    $data=Join-Path $OutputDirectory 'upgrade-data'
    $env:VICTUS_DATA_DIR=$data
    $env:VICTUS_API_TOKEN=[Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
    $headers=@{Authorization='Bearer '+$env:VICTUS_API_TOKEN}
    Launch $old 'prior'
    $body=@{tool='fs.create_note';arguments=@{filename='prior-proof.txt';text='Prior artifact proof'}}|ConvertTo-Json -Depth 4
    $queued=Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8765/api/tasks' -Headers $headers -ContentType 'application/json' -Body $body
    Check 'prior_binary_verified_note' (Wait-Task $queued.task_id).verified
    Stop-Owned
    $report.prior_schema=((Invoke-VictusOffline $old @('migrate'))|ConvertFrom-Json).schema
    $backup=Join-Path $OutputDirectory 'prior-backup'
    $null=Invoke-VictusOffline $old @('backup','--destination',$backup)
    # Preserve old data; migrate only a separate checksum-verified restored copy.
    $candidateData=Join-Path $OutputDirectory 'candidate-data'
    $null=Invoke-VictusOffline $new @('restore','--source',$backup,'--destination',$candidateData)
    $data=$candidateData
    $env:VICTUS_DATA_DIR=$candidateData
    $migration=(Invoke-VictusOffline $new @('migrate'))|ConvertFrom-Json
    $report.candidate_schema=$migration.schema
    $report.schema_changed=$migration.schema -gt $report.prior_schema
    Check 'compatible_schema_migration' ($migration.schema -ge $report.prior_schema)
    Launch $new 'candidate'
    Check 'candidate_preserves_prior_bytes' ((Get-Content -LiteralPath (Join-Path $data 'workspace/prior-proof.txt') -Raw) -eq 'Prior artifact proof')
    $commandHeaders=@{Authorization=$headers.Authorization;'X-Client-Request-ID'='upgrade-command'}
    $command=Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8765/api/commands' -Headers $commandHeaders -ContentType 'application/json' -Body '{"text":"Create a note upgraded.txt containing \"Candidate artifact proof\""}'
    Check 'candidate_command_verified' (Wait-Task $command.task_id).verified
    Stop-Owned
    $rollback=Join-Path $OutputDirectory 'rollback-data'
    $null=Invoke-VictusOffline $old @('restore','--source',$backup,'--destination',$rollback)
    $env:VICTUS_DATA_DIR=$rollback
    Launch $old 'rollback'
    Check 'prior_binary_rollback_bytes' ((Get-Content -LiteralPath (Join-Path $rollback 'workspace/prior-proof.txt') -Raw) -eq 'Prior artifact proof')
    Check 'rollback_excludes_candidate_effect' (-not (Test-Path -LiteralPath (Join-Path $rollback 'workspace/upgraded.txt')))
    Stop-Owned
    Check 'prior_bundle_preserved' ((Get-FileHash -LiteralPath (Join-Path $PriorBundle 'release-manifest.json') -Algorithm SHA256).Hash -eq $priorHash)
    $finalIntegrity=(Invoke-VictusOffline $new @('verify-bundle'))|ConvertFrom-Json
    Check 'candidate_bundle_preserved' ($finalIntegrity.bundle_manifest_sha256 -eq $report.candidate_manifest_sha256)
    $finalPrior=(Invoke-VictusOffline $new @('verify-bundle','--source',$PriorBundle))|ConvertFrom-Json
    Check 'prior_inventory_preserved' ($finalPrior.bundle_manifest_sha256 -eq $report.prior_manifest_sha256)
    $report.passed=$true
}catch{
    $report.failure='UPGRADE_ROLLBACK_FAILED_OR_BLOCKED'
    Write-Warning 'Prior-artifact check failed or was blocked. Review the private local logs.'
}finally{
    try{
        if($server -and -not $server.HasExited){$report.forced_server_terminations++;$server.Kill();if(-not $server.WaitForExit(10000)){throw 'Owned cleanup deadline'}}
        $report.cleanup_complete=$true
    }catch{$report.cleanup_complete=$false;$report.passed=$false}
    foreach($name in $names){[Environment]::SetEnvironmentVariable($name,$saved[$name],'Process')}
    $report|ConvertTo-Json -Depth 6|Set-Content -LiteralPath (Join-Path $OutputDirectory 'report.json')
}
if(-not $report.passed){exit 1}
