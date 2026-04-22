$ErrorActionPreference = "SilentlyContinue"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo

$logDir = Join-Path $repo "outputs\hook_logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$logFile = Join-Path $logDir "pre-commit-$stamp.log"

"[pre-commit] start $stamp" | Out-File -FilePath $logFile -Encoding utf8
uv run pytest tests/test_settings.py tests/test_preprocessing.py tests/test_sentiment.py tests/test_pipeline.py *>> $logFile
if ($LASTEXITCODE -ne 0) {
    "[pre-commit] verification failed" | Out-File -FilePath $logFile -Encoding utf8 -Append
    exit 1
}
"[pre-commit] verification passed" | Out-File -FilePath $logFile -Encoding utf8 -Append
exit 0
