# ASCII ONLY: PowerShell 5.1 decodes BOM-less files as ANSI/GBK; CJK chars can corrupt parsing.
# Official P0 eval runner: real LLM (DashScope Qwen) + self-heal comparison, 50 questions x 2 runs.
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File eval\run_full_eval.ps1
#   powershell ... -File eval\run_full_eval.ps1 -Proxy ''   (machine without local proxy)
# Expected duration: about 6-15 minutes (about 3s per question, plus self-heal retries).
param([string]$Proxy = 'http://127.0.0.1:7897')

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot

# The key lives in User-scope registry; process snapshots may not have it. Never echo it.
$env:DASHSCOPE_API_KEY = [Environment]::GetEnvironmentVariable('DASHSCOPE_API_KEY', 'User')
if (-not $env:DASHSCOPE_API_KEY) { throw 'DASHSCOPE_API_KEY not found in User scope' }

# Registry proxy may carry an https:// scheme that breaks TLS-in-TLS; force http:// when enabled.
if ($Proxy) {
    $env:HTTP_PROXY  = $Proxy
    $env:HTTPS_PROXY = $Proxy
    $env:NO_PROXY    = 'localhost,127.0.0.1'
}

Remove-Item Env:NL2SQL_EVAL_LIMIT -ErrorAction SilentlyContinue
Remove-Item Env:NL2SQL_EVAL_RESULTS -ErrorAction SilentlyContinue
Remove-Item Env:NL2SQL_EVAL_REPORT -ErrorAction SilentlyContinue

$py  = Join-Path $root 'backend\.venv\Scripts\python.exe'
$log = Join-Path $root 'eval\run_log.txt'
# PS 5.1: with ErrorActionPreference='Stop', native stderr via 2>&1 becomes a terminating error;
# use Continue here so stderr warnings stream through, and rely on $LASTEXITCODE for failure.
$ErrorActionPreference = 'Continue'
& $py (Join-Path $root 'eval\run_eval.py') 2>&1 | Tee-Object -FilePath $log
exit $LASTEXITCODE
