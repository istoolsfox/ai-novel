$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "../..")
Set-Location $Root

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker was not found. Install and start Docker Desktop first."
}

$EnvFile = Join-Path $Root ".env"
$EnvTemplate = Join-Path $Root "deploy/.env.example"
$EnvExists = Test-Path -LiteralPath $EnvFile
$TemplateExists = Test-Path -LiteralPath $EnvTemplate

if ((-not $EnvExists) -and $TemplateExists) {
    Copy-Item -LiteralPath $EnvTemplate -Destination $EnvFile
    Write-Host "Created .env from deploy/.env.example."
}

$Port = "8080"
if ($env:AI_NOVEL_PORT) {
    $Port = $env:AI_NOVEL_PORT
}

docker compose up -d --build
if ($LASTEXITCODE -ne 0) {
    throw "Docker Compose failed with exit code $LASTEXITCODE."
}

Write-Host "AI Novel Workbench is running at http://127.0.0.1:$Port"
docker compose ps
