$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$frontendDir = Join-Path $root "frontend"
$packageFile = Join-Path $frontendDir "package.json"
$nodeModulesDir = Join-Path $frontendDir "node_modules"
$stampFile = Join-Path $frontendDir ".package.sha256"
$nextCacheDir = Join-Path $frontendDir ".next"

Set-Location $frontendDir

$env:NEXT_PUBLIC_API_BASE_URL = "http://localhost:8000/api"

$packageHash = (Get-FileHash $packageFile -Algorithm SHA256).Hash
$installedHash = if (Test-Path $stampFile) { (Get-Content $stampFile -Raw).Trim() } else { "" }

if (!(Test-Path $nodeModulesDir) -or $packageHash -ne $installedHash) {
  cmd /c npm install
  Set-Content -Path $stampFile -Value $packageHash -NoNewline
}

if (Test-Path $nextCacheDir) {
  try {
    Remove-Item -LiteralPath $nextCacheDir -Recurse -Force -ErrorAction Stop
  } catch {
    Write-Warning "Could not clear .next cache because Windows is still holding a file lock. Continuing with the existing cache."
  }
}

cmd /c npm run dev
