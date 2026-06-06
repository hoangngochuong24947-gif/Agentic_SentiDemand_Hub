$ErrorActionPreference = "SilentlyContinue"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo

$logDir = Join-Path $repo "outputs\hook_logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$logFile = Join-Path $logDir "post-merge-$stamp.log"
$skillsFile = Join-Path $repo "docs\Skills.md"

"[post-merge] merged at $stamp" | Out-File -FilePath $logFile -Encoding utf8
uv sync *>> $logFile

$latestError = Get-ChildItem $logDir -Filter "*.log" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($latestError) {
    $snippet = Get-Content $latestError.FullName | Select-Object -Last 20
    Add-Content -Path $skillsFile -Value "`n## $stamp`n"
    Add-Content -Path $skillsFile -Value "最近一次 hook / merge 复盘："
    $snippet | Add-Content -Path $skillsFile
}
