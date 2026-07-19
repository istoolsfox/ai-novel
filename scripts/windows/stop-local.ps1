$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "../..")
$StatePath = Join-Path $Root ".runtime/local-processes.json"

if (-not (Test-Path $StatePath)) {
    Write-Host "没有找到本地进程记录。"
    exit 0
}

$State = Get-Content $StatePath -Raw | ConvertFrom-Json
foreach ($Name in @("frontend", "worker", "backend")) {
    $ProcessId = [int]$State.$Name
    if ($ProcessId -gt 0) {
        Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
        Write-Host "已停止 $Name，PID $ProcessId"
    }
}

Remove-Item $StatePath -Force
