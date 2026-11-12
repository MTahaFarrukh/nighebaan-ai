$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path $PSScriptRoot -Parent
$backendRoot = Join-Path $repoRoot 'backend'
$frontendRoot = Join-Path $repoRoot 'frontend'
$python = Join-Path $backendRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Backend environment missing. Read README setup instructions.' }
if (-not (Test-Path -LiteralPath (Join-Path $frontendRoot 'node_modules/vite/bin/vite.js'))) { throw 'Run npm ci in frontend first.' }
function Is-Ready([string]$url, [string]$expected) {
    try { return (Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 5).Content.Contains($expected) } catch { return $false }
}
if (-not (Is-Ready 'http://127.0.0.1:8000/' 'Nigehbaan')) {
    Start-Process -FilePath $python -ArgumentList '-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000','--no-access-log' -WorkingDirectory $backendRoot -WindowStyle Hidden | Out-Null
}
if (-not (Is-Ready 'http://localhost:5173/' 'Nigehbaan AI')) {
    $node = (Get-Command node -ErrorAction Stop).Source
    Start-Process -FilePath $node -ArgumentList 'node_modules/vite/bin/vite.js','--host','localhost','--strictPort' -WorkingDirectory $frontendRoot -WindowStyle Hidden | Out-Null
}
for ($attempt=0; $attempt -lt 15; $attempt++) {
    if ((Is-Ready 'http://127.0.0.1:8000/' 'Nigehbaan') -and (Is-Ready 'http://localhost:5173/' 'Nigehbaan AI')) {
        Write-Output 'Ready: http://localhost:5173/#/analyze'
        Write-Output 'API docs: http://127.0.0.1:8000/docs'
        exit 0
    }
    Start-Sleep -Seconds 1
}
throw 'Preview did not become ready. Check port 8000/5173 conflicts and installed dependencies. No existing process was stopped.'
