$ErrorActionPreference = "SilentlyContinue"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo

$logDir = Join-Path $repo "outputs\hook_logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$logFile = Join-Path $logDir "post-commit-$stamp.log"
$summaryFile = Join-Path $repo "docs\commit-learning-log.md"

"[post-commit] $(git rev-parse --short HEAD)" | Out-File -FilePath $logFile -Encoding utf8
git log -1 --stat | Out-File -FilePath $logFile -Encoding utf8 -Append
Add-Content -Path $summaryFile -Value "`n## $stamp`n"
git log -1 --pretty=format:"%h %s" | Add-Content -Path $summaryFile
git log -1 --stat --pretty="" | Add-Content -Path $summaryFile
