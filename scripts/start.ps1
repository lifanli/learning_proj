[CmdletBinding()]
param(
    [switch]$SkipBuild,
    [switch]$SkipInstall,
    [switch]$NoBrowser,
    [switch]$BuildOnly,
    [switch]$NoConda,
    [switch]$InstallPythonDeps,
    [switch]$KeepExistingServer,
    [switch]$ForcePortKill,
    [string]$CondaEnv = "study-proj",
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

function Invoke-Native {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $FilePath $($Arguments -join ' ')"
    }
}

function Assert-Command {
    param([Parameter(Mandatory = $true)][string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' was not found in PATH."
    }
}

function Get-PortOwnerProcesses {
    param([Parameter(Mandatory = $true)][int]$TargetPort)

    $connections = Get-NetTCPConnection -LocalPort $TargetPort -State Listen -ErrorAction SilentlyContinue
    foreach ($connection in $connections) {
        Get-CimInstance Win32_Process -Filter "ProcessId=$($connection.OwningProcess)" -ErrorAction SilentlyContinue
    }
}

function Wait-PortReleased {
    param(
        [Parameter(Mandatory = $true)][int]$TargetPort,
        [int]$TimeoutSeconds = 10
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $stillListening = Get-NetTCPConnection -LocalPort $TargetPort -State Listen -ErrorAction SilentlyContinue
        if (-not $stillListening) {
            return
        }
        Start-Sleep -Milliseconds 300
    }

    throw "Port $TargetPort is still in use after waiting $TimeoutSeconds seconds."
}

function Ensure-PortAvailable {
    param(
        [Parameter(Mandatory = $true)][int]$TargetPort,
        [Parameter(Mandatory = $true)][string]$WorkspaceRoot
    )

    if ($KeepExistingServer) {
        return
    }

    $owners = @(Get-PortOwnerProcesses -TargetPort $TargetPort)
    if (-not $owners) {
        return
    }

    foreach ($owner in $owners) {
        $cmd = [string]$owner.CommandLine
        $name = [string]$owner.Name
        $isProjectServer = $cmd -match 'run_api\.py' -or $cmd -match 'src\.webapi\.app' -or $cmd -match 'uvicorn'

        if ($isProjectServer -or $ForcePortKill) {
            Write-Host "Stopping existing process on port ${TargetPort}: PID=$($owner.ProcessId), $name"
            Write-Host "CommandLine: $cmd"
            Stop-Process -Id $owner.ProcessId -Force -ErrorAction Stop
        } else {
            throw @"
Port $TargetPort is already in use by PID=$($owner.ProcessId), $name.
CommandLine: $cmd

This does not look like this project's API server, so it was not stopped automatically.
Use -Port <other-port> or pass -ForcePortKill if you intentionally want to stop it.
"@
        }
    }

    Wait-PortReleased -TargetPort $TargetPort
}

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Frontend = Join-Path $Root "frontend"
$DistIndex = Join-Path $Frontend "dist\index.html"

Set-Location $Root

Write-Host "== Study Project one-click startup =="
Write-Host "Workspace: $Root"

if ($NoConda) {
    Assert-Command "python"
    Write-Host "Python runtime: current shell python"
} else {
    Assert-Command "conda"
    Write-Host "Python runtime: conda env '$CondaEnv'"
    Invoke-Native "conda" "run" "-n" $CondaEnv "python" "--version"

    if ($InstallPythonDeps) {
        Write-Host "Installing Python dependencies into conda env '$CondaEnv'..."
        Invoke-Native "conda" "run" "--no-capture-output" "-n" $CondaEnv "python" "-m" "pip" "install" "-r" "requirements.txt"
    }
}

if (-not $SkipBuild) {
    Assert-Command "npm"

    Push-Location $Frontend
    try {
        $needsInstall = -not (Test-Path "node_modules") -or -not (Test-Path "node_modules\vite\package.json")
        if ($needsInstall -and -not $SkipInstall) {
            Write-Host "Installing frontend dependencies..."
            Invoke-Native "npm" "install"
        }

        Write-Host "Building Vue frontend..."
        try {
            Invoke-Native "npm" "run" "build"
        } catch {
            if ($SkipInstall) {
                throw
            }

            Write-Host "Frontend build failed once; refreshing npm dependencies and retrying..."
            Invoke-Native "npm" "install"
            Invoke-Native "npm" "run" "build"
        }
    } finally {
        Pop-Location
    }
}

if (-not (Test-Path $DistIndex)) {
    throw "frontend/dist/index.html was not found. Run: cd frontend; npm install; npm run build"
}

if ($BuildOnly) {
    Write-Host "Build complete. Start later with: .\start.bat"
    exit 0
}

Ensure-PortAvailable -TargetPort $Port -WorkspaceRoot $Root

$Url = "http://localhost:$Port"
$env:STUDY_PROJ_HOST = $HostAddress
$env:STUDY_PROJ_PORT = [string]$Port

Write-Host "Starting integrated API + frontend service..."
Write-Host "Open: $Url"
Write-Host "Press Ctrl+C to stop."

if (-not $NoBrowser) {
    Start-Process $Url
}

if ($NoConda) {
    Invoke-Native "python" "run_api.py"
} else {
    Invoke-Native "conda" "run" "--no-capture-output" "-n" $CondaEnv "python" "run_api.py"
}
