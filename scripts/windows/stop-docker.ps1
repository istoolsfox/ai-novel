$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "../..")
Set-Location $Root

docker compose down
Write-Host "AI 小说系统已停止。数据卷仍然保留。"
