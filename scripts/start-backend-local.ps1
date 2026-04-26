param(
  [switch]$NoReload
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $root "backend"
$venvDir = Join-Path $backendDir ".venv"
$envFile = Join-Path $root ".env"
$requirementsFile = Join-Path $backendDir "requirements.txt"
$stampFile = Join-Path $venvDir ".requirements.sha256"

Set-Location $backendDir

if (Test-Path $envFile) {
  Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -match '^\s*$') {
      return
    }
    $parts = $_ -split '=', 2
    if ($parts.Length -eq 2) {
      $name = $parts[0].Trim()
      $value = $parts[1].Trim()
      [System.Environment]::SetEnvironmentVariable($name, $value, "Process")
    }
  }
}

if (!(Test-Path $venvDir)) {
  python -m venv .venv
}

$pythonExe = Join-Path $venvDir "Scripts\\python.exe"
$pipExe = Join-Path $venvDir "Scripts\\pip.exe"

$requirementsHash = (Get-FileHash $requirementsFile -Algorithm SHA256).Hash
$installedHash = if (Test-Path $stampFile) { (Get-Content $stampFile -Raw).Trim() } else { "" }

if ($requirementsHash -ne $installedHash) {
  & $pipExe install -r requirements.txt
  Set-Content -Path $stampFile -Value $requirementsHash -NoNewline
}

$env:DATABASE_URL = "sqlite:///./study_assistant.db"
$env:BACKEND_CORS_ORIGINS = "http://localhost:3000"

if (!(Test-Path (Join-Path $backendDir "storage\\uploads"))) {
  New-Item -ItemType Directory -Force -Path (Join-Path $backendDir "storage\\uploads") | Out-Null
}

$uvicornArgs = @("-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000")
if (-not $NoReload) {
  $uvicornArgs += "--reload"
}

& $pythonExe @uvicornArgs
