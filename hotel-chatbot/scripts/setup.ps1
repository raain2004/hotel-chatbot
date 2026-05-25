# Thiết lập môi trường Hotel Chatbot (Docker)
$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

Write-Host "=== Hotel Chatbot Setup ===" -ForegroundColor Cyan

if (-not (Test-Path ".env")) {
    Write-Host "Chua co .env — copy tu .env.example va dien thong tin."
    Copy-Item ".env.example" ".env"
    exit 1
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Can cai Docker Desktop." -ForegroundColor Red
    exit 1
}

Write-Host "`n[1/4] Khoi dong PostgreSQL..." -ForegroundColor Yellow
docker compose up -d db
$max = 30
for ($i = 0; $i -lt $max; $i++) {
    $h = docker compose ps db --format json 2>$null | ConvertFrom-Json
    if ($h.Health -eq "healthy") { break }
    Start-Sleep -Seconds 2
}
Write-Host "PostgreSQL san sang." -ForegroundColor Green

Write-Host "`n[2/4] Chay tests..." -ForegroundColor Yellow
docker compose -f docker-compose.test.yml run --rm test
if ($LASTEXITCODE -ne 0) {
    Write-Host "Tests FAILED." -ForegroundColor Red
    exit $LASTEXITCODE
}
Write-Host "Tests PASSED." -ForegroundColor Green

Write-Host "`n[3/4] Build va khoi dong API..." -ForegroundColor Yellow
docker compose up -d --build api
Start-Sleep -Seconds 5

Write-Host "`n[4/4] Seed du lieu mau..." -ForegroundColor Yellow
try {
    $r = Invoke-RestMethod -Uri "http://localhost:8000/api/dev/seed" -Method POST -TimeoutSec 30
    Write-Host $r.message -ForegroundColor Green
} catch {
    Write-Host "Seed chua chay duoc (API dang khoi dong?). Thu lai: curl -X POST http://localhost:8000/api/dev/seed"
}

Write-Host "`n=== Xong ===" -ForegroundColor Cyan
Write-Host "Swagger:  http://localhost:8000/docs"
Write-Host "Health:   http://localhost:8000/health"
Write-Host "Admin key: xem file .env (ADMIN_API_KEY)"
Write-Host "Huong dan Meta/ngrok: docs/CAI_DAT_THU_CONG.md"
