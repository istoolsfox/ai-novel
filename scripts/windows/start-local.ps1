$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "../..")
$RuntimeDir = Join-Path $Root ".runtime"
New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null

$PythonCommand = Get-Command python -ErrorAction SilentlyContinue
if (-not $PythonCommand) {
    throw "未找到 Python。"
}
$NpmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
if (-not $NpmCommand) {
    $NpmCommand = Get-Command npm -ErrorAction SilentlyContinue
}
if (-not $NpmCommand) {
    throw "未找到 npm。"
}

$Backend = Start-Process -FilePath $PythonCommand.Source -ArgumentList @("-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", "8000") -WorkingDirectory $Root -PassThru
$Worker = Start-Process -FilePath $PythonCommand.Source -ArgumentList @("-m", "backend.app.runtime_worker", "--poll-interval", "1") -WorkingDirectory $Root -PassThru
$Frontend = Start-Process -FilePath $NpmCommand.Source -ArgumentList @("run", "dev", "--", "--host", "127.0.0.1") -WorkingDirectory (Join-Path $Root "frontend") -PassThru

@{
    backend = $Backend.Id
    worker = $Worker.Id
    frontend = $Frontend.Id
} | ConvertTo-Json | Set-Content -Path (Join-Path $RuntimeDir "local-processes.json") -Encoding UTF8

Write-Host "本地服务已启动："
Write-Host "  前端：http://127.0.0.1:5173"
Write-Host "  后端：http://127.0.0.1:8000"
Write-Host "  Worker PID：$($Worker.Id)"
