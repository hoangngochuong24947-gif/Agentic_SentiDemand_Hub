$ErrorActionPreference = "SilentlyContinue"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo

$logDir = Join-Path $repo "outputs\hook_logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$logFile = Join-Path $logDir "pre-commit-$stamp.log"

"[pre-commit] start $stamp" | Out-File -FilePath $logFile -Encoding utf8

$changed = git diff --cached --name-only
$requiresReadme = $false
foreach ($path in $changed) {
    if ($path -match "^(src|config|scripts|tests|data|examples)/" -or $path -match "^(pyproject\.toml|requirements\.txt|uv\.lock)$") {
        $requiresReadme = $true
        break
    }
}

if ($requiresReadme -and -not ($changed -contains "README.md")) {
    "[pre-commit] README.md update required for source/config/script/test/data changes" | Out-File -FilePath $logFile -Encoding utf8 -Append
    Write-Host "README.md must be staged when committing source, config, script, test, or data changes." -ForegroundColor Red
    Write-Host "Update README.md with the workflow, validation steps, or user-facing impact, then stage it." -ForegroundColor Yellow
    exit 1
}

uv run pytest tests/test_settings.py tests/test_preprocessing.py tests/test_sentiment.py tests/test_pipeline.py *>> $logFile
if ($LASTEXITCODE -ne 0) {
    "[pre-commit] verification failed" | Out-File -FilePath $logFile -Encoding utf8 -Append
    exit 1
}
"[pre-commit] verification passed" | Out-File -FilePath $logFile -Encoding utf8 -Append
exit 0
