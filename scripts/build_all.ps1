"""一键打包脚本（Windows PowerShell 版）。

用法：
    powershell -ExecutionPolicy Bypass -File scripts\build_all.ps1

步骤：
    1. 构建前端（Vite build）
    2. 构建后端 sidecar（PyInstaller）
    3. 构建 Tauri 应用（cargo tauri build）
"""
$ErrorActionPreference = "Stop"

$Root = Resolve-Path "$PSScriptRoot\.."
Write-Host "[build_all] ROOT = $Root" -ForegroundColor Cyan

# Step 1: 构建前端
Write-Host "`n=== Step 1/3: 构建前端 ===" -ForegroundColor Yellow
Push-Location "$Root\frontend"
try {
    if (-not (Test-Path "node_modules")) {
        Write-Host "安装前端依赖..."
        npm install
    }
    $env:VITE_TAURI = "true"
    npm run build
    if ($LASTEXITCODE -ne 0) { throw "前端构建失败" }
    Write-Host "前端构建完成" -ForegroundColor Green
} finally {
    Pop-Location
}

# Step 2: 构建 sidecar
Write-Host "`n=== Step 2/3: 构建后端 sidecar ===" -ForegroundColor Yellow
& python "$Root\scripts\build_sidecar.py"
if ($LASTEXITCODE -ne 0) { throw "Sidecar 构建失败" }
Write-Host "Sidecar 构建完成" -ForegroundColor Green

# Step 3: 构建 Tauri 应用
Write-Host "`n=== Step 3/3: 构建 Tauri 应用 ===" -ForegroundColor Yellow
Push-Location "$Root\desktop"
try {
    cargo tauri build
    if ($LASTEXITCODE -ne 0) { throw "Tauri 构建失败" }
    Write-Host "Tauri 构建完成" -ForegroundColor Green
} finally {
    Pop-Location
}

Write-Host "`n=== 全部构建完成 ===" -ForegroundColor Cyan
Write-Host "安装包位于：$Root\desktop\target\release\bundle\" -ForegroundColor Cyan
