[CmdletBinding()]
param(
    [int]$Port = 8000,
    [switch]$ForcePortKill
)

$ErrorActionPreference = "Stop"

$connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if (-not $connections) {
    Write-Host "No process is listening on port $Port."
    exit 0
}

foreach ($connection in $connections) {
    $process = Get-CimInstance Win32_Process -Filter "ProcessId=$($connection.OwningProcess)" -ErrorAction SilentlyContinue
    if (-not $process) {
        continue
    }

    $commandLine = [string]$process.CommandLine
    $isProjectServer = $commandLine -match 'run_api\.py' -or $commandLine -match 'src\.webapi\.app' -or $commandLine -match 'uvicorn'

    if ($isProjectServer -or $ForcePortKill) {
        Write-Host "Stopping PID=$($process.ProcessId), $($process.Name)"
        Write-Host "CommandLine: $commandLine"
        Stop-Process -Id $process.ProcessId -Force -ErrorAction Stop
    } else {
        Write-Host "Port $Port is used by PID=$($process.ProcessId), $($process.Name), but it does not look like this project."
        Write-Host "CommandLine: $commandLine"
        Write-Host "Use -ForcePortKill if you intentionally want to stop it."
    }
}
