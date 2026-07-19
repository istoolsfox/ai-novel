$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "../..")
Set-Location $Root

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "未找到 Docker。请先安装 Docker Desktop。"
}

if (-not (Test-Path ".env") -and (Test-Path "deploy/.env.example")) {
    Copy-Item "deploy/.env.example" ".env"
    Write-Host "已从 deploy/.env.example 创建 .env。"
}

docker compose up -d --build
Write-Host "AI 小说系统已启动：http://127.0.0.1:$($env:AI_NOVEL_PORT ?? '8080')"
docker compose ps
