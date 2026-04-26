$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$backendScript = Join-Path $root "scripts\start-backend-local.ps1"
$frontendScript = Join-Path $root "scripts\start-frontend-local.ps1"
$envFile = Join-Path $root ".env"
$envExample = Join-Path $root ".env.example"
$runLogsDir = Join-Path $root "run-logs"
$pidFile = Join-Path $runLogsDir "local-start-pids.json"

function Write-Step {
  param([string]$Message)
  Write-Host "[Study Assistant] $Message"
}

function Test-Port {
  param(
    [string]$HostName,
    [int]$Port
  )

  $client = [System.Net.Sockets.TcpClient]::new()
  try {
    $connect = $client.BeginConnect($HostName, $Port, $null, $null)
    if (-not $connect.AsyncWaitHandle.WaitOne(500, $false)) {
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

function Wait-ForPort {
  param(
    [string]$Name,
    [int]$Port,
    [int]$TimeoutSeconds = 180
  )

  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  while ((Get-Date) -lt $deadline) {
    if (Test-Port -HostName "127.0.0.1" -Port $Port) {
      Write-Step "$Name is ready on port $Port."
      return $true
    }
    Start-Sleep -Milliseconds 700
  }

  Write-Step "$Name did not report ready within $TimeoutSeconds seconds. It may still be installing dependencies or starting; check the logs below."
  return $false
}

function Stop-ProcessTree {
  param([int]$ProcessId)

  $children = Get-CimInstance Win32_Process -Filter "ParentProcessId = $ProcessId" -ErrorAction SilentlyContinue
  foreach ($child in $children) {
    Stop-ProcessTree -ProcessId $child.ProcessId
  }

  Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
}

if (!(Test-Path $envFile) -and (Test-Path $envExample)) {
  Copy-Item -Path $envExample -Destination $envFile
  Write-Step "Created .env from .env.example."
}

if (!(Test-Path $runLogsDir)) {
  New-Item -ItemType Directory -Force -Path $runLogsDir | Out-Null
}

Write-Step "Starting backend and frontend in separate service windows..."

$backend = Start-Process -FilePath "powershell.exe" `
  -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $backendScript, "-NoReload") `
  -WorkingDirectory $root `
  -WindowStyle Normal `
  -PassThru

$frontend = Start-Process -FilePath "powershell.exe" `
  -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $frontendScript) `
  -WorkingDirectory $root `
  -WindowStyle Normal `
  -PassThru

@{
  started_at = (Get-Date).ToString("o")
  backend_launcher_pid = $backend.Id
  frontend_launcher_pid = $frontend.Id
  ports = @(3000, 8000)
} | ConvertTo-Json | Set-Content -Path $pidFile -Encoding UTF8

try {
  Wait-ForPort -Name "Backend" -Port 8000 | Out-Null
  Wait-ForPort -Name "Frontend" -Port 3000 | Out-Null

  Write-Host ""
  Write-Host "Frontend: http://localhost:3000"
  Write-Host "Backend:  http://localhost:8000"
  Write-Host "Swagger:  http://localhost:8000/docs"
  Write-Host ""
  Write-Host "The backend and frontend service windows show live logs."
  Write-Host "Press Ctrl+C in this launcher window to stop both services."

  Wait-Process -Id @($backend.Id, $frontend.Id)
} finally {
  Write-Step "Stopping services..."
  Stop-ProcessTree -ProcessId $frontend.Id
  Stop-ProcessTree -ProcessId $backend.Id
  Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
}
