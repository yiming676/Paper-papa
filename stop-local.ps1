$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$pidFile = Join-Path $root "run-logs\local-start-pids.json"

function Write-Step {
  param([string]$Message)
  Write-Host "[Study Assistant] $Message"
}

function Stop-ProcessTree {
  param([int]$ProcessId)

  $process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
  if (-not $process) {
    return
  }

  $children = Get-CimInstance Win32_Process -Filter "ParentProcessId = $ProcessId" -ErrorAction SilentlyContinue
  foreach ($child in $children) {
    Stop-ProcessTree -ProcessId $child.ProcessId
  }

  Write-Step "Stopping process $ProcessId ($($process.ProcessName))."
  Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
}

function Stop-ListeningPort {
  param([int]$Port)

  $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
  $processIds = $connections | Select-Object -ExpandProperty OwningProcess -Unique

  foreach ($processId in $processIds) {
    if ($processId -and $processId -ne 0) {
      Stop-ProcessTree -ProcessId $processId
    }
  }
}

if (Test-Path $pidFile) {
  $pids = Get-Content -Raw $pidFile | ConvertFrom-Json
  Stop-ProcessTree -ProcessId ([int]$pids.frontend_launcher_pid)
  Stop-ProcessTree -ProcessId ([int]$pids.backend_launcher_pid)
  Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
}

Stop-ListeningPort -Port 3000
Stop-ListeningPort -Port 8000

Write-Step "Local services stopped."
