# Start the API (uvicorn) and UI (Streamlit) of every project - or only the ones you list - in the background.
#   .\scripts\start_all.ps1                 # all five projects
#   .\scripts\start_all.ps1 -Projects 01,03 # only projects 01 and 03
#   .\scripts\stop_all.ps1                  # stop everything again
# Logs go to <project>\logs\api.log / ui.log. Uses the shared portfolio .venv.
# Ollama must be running for LLM answers (refusals, search and ML predictions work without it).
param([string[]]$Projects = @("01", "02", "03", "04", "05"))

$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { Write-Error "Create the shared venv first (see README Quick start)."; exit 1 }

$apps = @{
    "01" = @{ dir = "01-payment-ops-intelligence";         api = "payops.api:app";       index = "payops.ingest" }
    "02" = @{ dir = "02-robotics-fleet-assistant";         api = "fleetops.api:app";     index = "fleetops.ingest" }
    "03" = @{ dir = "03-supply-chain-knowledge-assistant"; api = "supplykb.api:app";     index = "supplykb.ingest" }
    "04" = @{ dir = "04-project-feasibility-ml";           api = "feasibility.api:app";  index = $null }
    "05" = @{ dir = "05-plant-assist";                     api = "plant_assist.api:app"; index = "plant_assist.ingest" }
}

foreach ($n in $Projects) {
    $app = $apps[$n]
    if ($null -eq $app) { Write-Warning "Unknown project $n"; continue }
    $dir = Join-Path $root $app.dir
    $apiPort = 8000 + [int]$n
    $uiPort = 8500 + [int]$n

    if (-not (Test-Path (Join-Path $dir ".env"))) { Copy-Item (Join-Path $dir ".env.example") (Join-Path $dir ".env") }
    if ($app.index -and -not (Test-Path (Join-Path $dir ".chroma"))) {
        Write-Host "[$n] building the vector index first (python -m $($app.index)) ..."
        Push-Location $dir; & $python -m $app.index; Pop-Location
    }
    New-Item -ItemType Directory -Force (Join-Path $dir "logs") | Out-Null

    if (Get-NetTCPConnection -LocalPort $apiPort -State Listen -ErrorAction SilentlyContinue) {
        Write-Host "[$n] API already running on :$apiPort"
    } else {
        Start-Process -FilePath $python -WorkingDirectory $dir -WindowStyle Hidden `
            -ArgumentList "-m", "uvicorn", $app.api, "--port", $apiPort `
            -RedirectStandardOutput (Join-Path $dir "logs\api.out.log") -RedirectStandardError (Join-Path $dir "logs\api.log")
    }
    if (Get-NetTCPConnection -LocalPort $uiPort -State Listen -ErrorAction SilentlyContinue) {
        Write-Host "[$n] UI already running on :$uiPort"
    } else {
        Start-Process -FilePath $python -WorkingDirectory $dir -WindowStyle Hidden `
            -ArgumentList "-m", "streamlit", "run", "ui/streamlit_app.py", "--server.port", $uiPort, "--server.headless", "true", "--browser.gatherUsageStats", "false" `
            -RedirectStandardOutput (Join-Path $dir "logs\ui.out.log") -RedirectStandardError (Join-Path $dir "logs\ui.log")
    }
    Write-Host ("[{0}] {1,-36} API http://localhost:{2}/docs   UI http://localhost:{3}" -f $n, $app.dir, $apiPort, $uiPort)
}
Write-Host "Starting up (first request can take 10-30 s while models and indexes load). Check: .\scripts\status.ps1"
