# Runs pytest in every project. No Ollama / Chroma needed (tests use fake LLMs and keyword retrievers).
$root = Split-Path -Parent $PSScriptRoot
$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }
$failed = @()
foreach ($p in Get-ChildItem $root -Directory | Where-Object { $_.Name -match '^\d\d-' }) {
    Write-Host "`n===== $($p.Name)" -ForegroundColor Cyan
    Push-Location $p.FullName
    & $py -m pytest -q -W ignore
    if ($LASTEXITCODE -ne 0) { $failed += $p.Name }
    Pop-Location
}
if ($failed) { Write-Host "`nFAILED: $($failed -join ', ')" -ForegroundColor Red; exit 1 }
Write-Host "`nAll projects passed." -ForegroundColor Green
