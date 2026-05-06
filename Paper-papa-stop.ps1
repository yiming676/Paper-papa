<#
Usage:
  1. Double-click Paper-papa-stop.cmd, or run this command in PowerShell:
     powershell.exe -NoProfile -ExecutionPolicy Bypass -File "F:\codex\Study-Assistant\Paper-papa-stop.ps1"
  2. The script CDs to F:\codex\Study-Assistant by itself.
  3. It stops only the backend and frontend processes recorded by Paper-papa.ps1.
#>

$ErrorActionPreference = "Stop"

$ProjectRoot = "F:\codex\Study-Assistant"
Set-Location -LiteralPath $ProjectRoot

$PidFile = Join-Path $ProjectRoot "run-logs\Paper-papa-pids.json"

function Write-Step {
  param([string]$Message)
  Write-Host "[Paper-papa] $Message"
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

  Write-Step "Stopping process $ProcessId ($($process.ProcessName))."
  Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
}

if (-not (Test-Path -LiteralPath $PidFile)) {
  Write-Step "No Paper-papa PID file found. Nothing to stop."
  return
}

$pids = Get-Content -Raw -Path $PidFile | ConvertFrom-Json

if ($pids.frontend_pid) {
  Stop-ProcessTree -ProcessId ([int]$pids.frontend_pid)
}
if ($pids.backend_pid) {
  Stop-ProcessTree -ProcessId ([int]$pids.backend_pid)
}
foreach ($processId in @($pids.frontend_listener_pids)) {
  if ($processId) {
    Stop-ProcessTree -ProcessId ([int]$processId)
  }
}
foreach ($processId in @($pids.backend_listener_pids)) {
  if ($processId) {
    Stop-ProcessTree -ProcessId ([int]$processId)
  }
}

Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
Write-Step "Services stopped."
