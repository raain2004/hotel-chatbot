# Chạy test suite — cần Python 3.11+ (bản ĐÃ CÀI, có python.exe)
# Ví dụ: $env:PYTHON_HOME = "D:\Python312"
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

$python = $null
if ($env:PYTHON_HOME -and (Test-Path "$env:PYTHON_HOME\python.exe")) {
    $python = "$env:PYTHON_HOME\python.exe"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $python = "python"
}

if ($python) {
    & $python -m pip install -r requirements.txt -q
    & $python -m pytest -v
    exit $LASTEXITCODE
}

if (Get-Command docker -ErrorAction SilentlyContinue) {
    docker compose -f docker-compose.test.yml run --rm test
    exit $LASTEXITCODE
}

Write-Host "Cần cài Python 3.11+ hoặc Docker để chạy tests."
exit 1
