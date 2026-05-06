<#
Usage:
  1. Double-click Paper-papa.cmd, or run this command in PowerShell:
     powershell.exe -NoProfile -ExecutionPolicy Bypass -File "F:\codex\Study-Assistant\Paper-papa.ps1"
  2. The script CDs to F:\codex\Study-Assistant by itself.
  3. It starts both backend and frontend, waits until both are ready, then opens the default browser.
  4. Preferred ports are backend 8000 and frontend 3000. If either port is busy, the script automatically uses the next free port.
  5. To stop services started by this script, run Paper-papa-stop.cmd.
#>

param(
  [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"

$ProjectRoot = "F:\codex\Study-Assistant"
$BackendPreferredPort = 8000
$FrontendPreferredPort = 3000
$PortSearchLimit = 60

Set-Location -LiteralPath $ProjectRoot

$BackendDir = Join-Path $ProjectRoot "backend"
$FrontendDir = Join-Path $ProjectRoot "frontend"
$RunLogsDir = Join-Path $ProjectRoot "run-logs"
$PidFile = Join-Path $RunLogsDir "Paper-papa-pids.json"
$EnvFile = Join-Path $ProjectRoot ".env"
$EnvExample = Join-Path $ProjectRoot ".env.example"

function Write-Step {
  param([string]$Message)
  Write-Host "[Paper-papa] $Message"
}

function Test-PortBusy {
  param([int]$Port)

  try {
    $listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop
    if ($listeners) {
      return $true
    }
  } catch {
  }

  $client = [System.Net.Sockets.TcpClient]::new()
  try {
    $connect = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
    if (-not $connect.AsyncWaitHandle.WaitOne(250, $false)) {
      return $false
    }
    $client.EndConnect($connect)
    return $true
  } catch {
    return $false
  } finally {
    $client.Close()
  }
}

function Get-FreePort {
  param(
    [int]$PreferredPort,
    [int]$SearchLimit
  )

  for ($port = $PreferredPort; $port -lt ($PreferredPort + $SearchLimit); $port++) {
    if (-not (Test-PortBusy -Port $port)) {
      return $port
    }
  }

  throw "No free port found from $PreferredPort to $($PreferredPort + $SearchLimit - 1)."
}

function Wait-ForPort {
  param(
    [string]$Name,
    [int]$Port,
    [System.Diagnostics.Process]$Process,
    [string]$ErrorLog,
    [int]$TimeoutSeconds = 240
  )

  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  while ((Get-Date) -lt $deadline) {
    $Process.Refresh()
    if ($Process.HasExited) {
      Write-Host ""
      Write-Step "$Name exited before it became ready. Error log:"
      if (Test-Path -LiteralPath $ErrorLog) {
        Get-Content -Path $ErrorLog -Tail 40
      }
      throw "$Name failed to start."
    }

    if (Test-PortBusy -Port $Port) {
      Write-Step "$Name is ready on port $Port."
      return
    }

    Start-Sleep -Milliseconds 700
  }

  throw "$Name did not become ready within $TimeoutSeconds seconds. Check $ErrorLog."
}

function Stop-ProcessTree {
  param([int]$ProcessId)

  $process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
  if (-not $process) {
    return
  }

  $children = Get-CimInstance Win32_Process -Filter "ParentProcessId = $ProcessId" -ErrorAction SilentlyContinue
  foreach ($child in $children) {
    Stop-ProcessTree -ProcessId ([int]$child.ProcessId)
  }

  Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
}

function Get-ListenerProcessIds {
  param([int]$Port)

  $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
  if (-not $connections) {
    return @()
  }

  return @($connections | Select-Object -ExpandProperty OwningProcess -Unique | Where-Object { $_ -and $_ -ne 0 })
}

function Stop-ExistingPaperPapa {
  if (-not (Test-Path -LiteralPath $PidFile)) {
    return
  }

  Write-Step "Found an existing Paper-papa PID file. Stopping the previous recorded services first."
  try {
    $old = Get-Content -Raw -Path $PidFile | ConvertFrom-Json
    if ($old.frontend_pid) {
      Stop-ProcessTree -ProcessId ([int]$old.frontend_pid)
    }
    if ($old.backend_pid) {
      Stop-ProcessTree -ProcessId ([int]$old.backend_pid)
    }
    foreach ($processId in @($old.frontend_listener_pids)) {
      if ($processId) {
        Stop-ProcessTree -ProcessId ([int]$processId)
      }
    }
    foreach ($processId in @($old.backend_listener_pids)) {
      if ($processId) {
        Stop-ProcessTree -ProcessId ([int]$processId)
      }
    }
  } finally {
    Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
  }
}

if (!(Test-Path -LiteralPath $ProjectRoot)) {
  throw "Project root does not exist: $ProjectRoot"
}

if (!(Test-Path -LiteralPath $RunLogsDir)) {
  New-Item -ItemType Directory -Force -Path $RunLogsDir | Out-Null
}

Stop-ExistingPaperPapa

if (!(Test-Path -LiteralPath $EnvFile) -and (Test-Path -LiteralPath $EnvExample)) {
  Copy-Item -Path $EnvExample -Destination $EnvFile
  Write-Step "Created .env from .env.example."
}

$BackendPort = Get-FreePort -PreferredPort $BackendPreferredPort -SearchLimit $PortSearchLimit
$FrontendPort = Get-FreePort -PreferredPort $FrontendPreferredPort -SearchLimit $PortSearchLimit

if ($BackendPort -ne $BackendPreferredPort) {
  Write-Step "Backend port $BackendPreferredPort is busy. Using $BackendPort."
}
if ($FrontendPort -ne $FrontendPreferredPort) {
  Write-Step "Frontend port $FrontendPreferredPort is busy. Using $FrontendPort."
}

$FrontendUrl = "http://localhost:$FrontendPort"
$BackendUrl = "http://localhost:$BackendPort"
$ApiUrl = "$BackendUrl/api"
$SwaggerUrl = "$BackendUrl/docs"

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$BackendOutLog = Join-Path $RunLogsDir "Paper-papa-backend-$timestamp.out.log"
$BackendErrLog = Join-Path $RunLogsDir "Paper-papa-backend-$timestamp.err.log"
$FrontendOutLog = Join-Path $RunLogsDir "Paper-papa-frontend-$timestamp.out.log"
$FrontendErrLog = Join-Path $RunLogsDir "Paper-papa-frontend-$timestamp.err.log"

function Import-DotEnv {
  if (-not (Test-Path -LiteralPath $EnvFile)) {
    return
  }

  Get-Content -Path $EnvFile | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -match '^\s*$') {
      return
    }
    $parts = $_ -split '=', 2
    if ($parts.Length -eq 2) {
      [System.Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), "Process")
    }
  }
}

function Ensure-BackendDependencies {
  Set-Location -LiteralPath $BackendDir

  $venvDir = Join-Path $BackendDir ".venv"
  $requirementsFile = Join-Path $BackendDir "requirements.txt"
  $stampFile = Join-Path $venvDir ".requirements.sha256"

  if (!(Test-Path -LiteralPath $venvDir)) {
    Write-Step "Creating backend virtual environment."
    python -m venv .venv
  }

  $pythonExe = Join-Path $venvDir "Scripts\python.exe"
  $pipExe = Join-Path $venvDir "Scripts\pip.exe"
  $requirementsHash = (Get-FileHash $requirementsFile -Algorithm SHA256).Hash
  $installedHash = if (Test-Path -LiteralPath $stampFile) { (Get-Content -Raw -Path $stampFile).Trim() } else { "" }

  if ($requirementsHash -ne $installedHash) {
    Write-Step "Installing backend dependencies."
    & $pipExe install -r requirements.txt
    Set-Content -Path $stampFile -Value $requirementsHash -NoNewline
  }

  $uploadDir = Join-Path $BackendDir "storage\uploads"
  if (!(Test-Path -LiteralPath $uploadDir)) {
    New-Item -ItemType Directory -Force -Path $uploadDir | Out-Null
  }

  Set-Location -LiteralPath $ProjectRoot
  return $pythonExe
}

function Ensure-FrontendDependencies {
  Set-Location -LiteralPath $FrontendDir

  $packageFile = Join-Path $FrontendDir "package.json"
  $nodeModulesDir = Join-Path $FrontendDir "node_modules"
  $stampFile = Join-Path $FrontendDir ".package.sha256"
  $packageHash = (Get-FileHash $packageFile -Algorithm SHA256).Hash
  $installedHash = if (Test-Path -LiteralPath $stampFile) { (Get-Content -Raw -Path $stampFile).Trim() } else { "" }

  if (!(Test-Path -LiteralPath $nodeModulesDir) -or $packageHash -ne $installedHash) {
    Write-Step "Installing frontend dependencies."
    npm.cmd install
    Set-Content -Path $stampFile -Value $packageHash -NoNewline
  }

  Set-Location -LiteralPath $ProjectRoot
}

Import-DotEnv
$env:DATABASE_URL = "sqlite:///./study_assistant.db"
$env:BACKEND_CORS_ORIGINS = $FrontendUrl
$env:NEXT_PUBLIC_API_BASE_URL = $ApiUrl

$PythonExe = Ensure-BackendDependencies
Ensure-FrontendDependencies

$BackendArgs = "/c `"$PythonExe`" -m uvicorn main:app --host 127.0.0.1 --port $BackendPort"
$FrontendArgs = "/c npm.cmd run dev -- -p $FrontendPort"

Write-Step "Starting backend on $BackendUrl ..."
$backend = Start-Process -FilePath "cmd.exe" `
  -ArgumentList $BackendArgs `
  -WorkingDirectory $BackendDir `
  -WindowStyle Hidden `
  -RedirectStandardOutput $BackendOutLog `
  -RedirectStandardError $BackendErrLog `
  -PassThru

Write-Step "Starting frontend on $FrontendUrl ..."
$frontend = Start-Process -FilePath "cmd.exe" `
  -ArgumentList $FrontendArgs `
  -WorkingDirectory $FrontendDir `
  -WindowStyle Hidden `
  -RedirectStandardOutput $FrontendOutLog `
  -RedirectStandardError $FrontendErrLog `
  -PassThru

@{
  started_at = (Get-Date).ToString("o")
  project_root = $ProjectRoot
  backend_pid = $backend.Id
  frontend_pid = $frontend.Id
  backend_port = $BackendPort
  frontend_port = $FrontendPort
  frontend_url = $FrontendUrl
  backend_url = $BackendUrl
  swagger_url = $SwaggerUrl
  backend_stdout = $BackendOutLog
  backend_stderr = $BackendErrLog
  frontend_stdout = $FrontendOutLog
  frontend_stderr = $FrontendErrLog
} | ConvertTo-Json | Set-Content -Path $PidFile -Encoding UTF8

try {
  Wait-ForPort -Name "Backend" -Port $BackendPort -Process $backend -ErrorLog $BackendErrLog
  Wait-ForPort -Name "Frontend" -Port $FrontendPort -Process $frontend -ErrorLog $FrontendErrLog
} catch {
  Stop-ProcessTree -ProcessId $frontend.Id
  Stop-ProcessTree -ProcessId $backend.Id
  Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
  throw
}

$BackendListenerPids = @(Get-ListenerProcessIds -Port $BackendPort)
$FrontendListenerPids = @(Get-ListenerProcessIds -Port $FrontendPort)

@{
  started_at = (Get-Date).ToString("o")
  project_root = $ProjectRoot
  backend_pid = $backend.Id
  frontend_pid = $frontend.Id
  backend_listener_pids = $BackendListenerPids
  frontend_listener_pids = $FrontendListenerPids
  backend_port = $BackendPort
  frontend_port = $FrontendPort
  frontend_url = $FrontendUrl
  backend_url = $BackendUrl
  swagger_url = $SwaggerUrl
  backend_stdout = $BackendOutLog
  backend_stderr = $BackendErrLog
  frontend_stdout = $FrontendOutLog
  frontend_stderr = $FrontendErrLog
} | ConvertTo-Json | Set-Content -Path $PidFile -Encoding UTF8

Write-Host ""
Write-Step "All services are ready."
Write-Host "Frontend: $FrontendUrl"
Write-Host "Backend:  $BackendUrl"
Write-Host "Swagger:  $SwaggerUrl"
Write-Host "Logs:     $RunLogsDir"
Write-Host ""

if (-not $NoBrowser) {
  Write-Step "Opening default browser..."
  Start-Process $FrontendUrl
}

Write-Step "Startup complete. Use Paper-papa-stop.cmd to stop the services."
