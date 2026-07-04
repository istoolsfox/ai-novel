$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$frontend = Join-Path $root "frontend"
$python = "python"
$npm = "npm.cmd"

function Test-PortListening {
    param([int]$Port)
    $connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    return $null -ne $connection
}

Write-Host "AI 小说创作平台一键启动" -ForegroundColor Cyan
Write-Host "项目目录: $root"

if (-not (Test-Path -LiteralPath (Join-Path $frontend "node_modules"))) {
    Write-Host "首次启动: 正在安装前端依赖..." -ForegroundColor Yellow
    Push-Location $frontend
    & $npm install
    Pop-Location
}

if (-not (Test-PortListening 8000)) {
    Write-Host "启动后端: http://127.0.0.1:8000" -ForegroundColor Green
    Start-Process powershell -ArgumentList @(
        "-NoExit",
        "-ExecutionPolicy", "Bypass",
        "-Command",
        "cd '$root'; $python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000"
    ) -WindowStyle Normal
} else {
    Write-Host "后端端口 8000 已在运行，跳过启动。" -ForegroundColor Yellow
}

if (-not (Test-PortListening 5173)) {
    Write-Host "启动前端: http://127.0.0.1:5173" -ForegroundColor Green
    Start-Process powershell -ArgumentList @(
        "-NoExit",
        "-ExecutionPolicy", "Bypass",
        "-Command",
        "cd '$frontend'; $npm run dev -- --host 127.0.0.1"
    ) -WindowStyle Normal
} else {
    Write-Host "前端端口 5173 已在运行，跳过启动。" -ForegroundColor Yellow
}

Start-Sleep -Seconds 3
Start-Process "http://127.0.0.1:5173"

Write-Host "已打开浏览器。如果页面尚未加载完成，请等前端窗口显示 Local 地址后刷新。" -ForegroundColor Cyan
