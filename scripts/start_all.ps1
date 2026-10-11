# Start the API (uvicorn) and UI (Streamlit) of every project - or only the ones you list - in the background.
#   .\scripts\start_all.ps1                    # all eight projects
#   .\scripts\start_all.ps1 -Projects 01,06    # only projects 01 and 06
#   .\scripts\stop_all.ps1                     # stop everything again
# Logs go to <project>\logs\api.log / ui.log. Uses the shared portfolio .venv.
# Ollama must be running for LLM answers (refusals, search and ML predictions work without it).
param([string[]]$Projects = @("01", "02", "03", "04", "05", "06", "07", "08"))

. (Join-Path $PSScriptRoot "projects.ps1")
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { Write-Error "Create the shared venv first (see README Quick start)."; exit 1 }

function Test-Port($port) { [bool](Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) }

foreach ($n in $Projects | ForEach-Object { "{0:D2}" -f [int]"$_" }) {   # "-Projects 7,08" and "07" both work
    $app = $PortfolioProjects[$n]
    if ($null -eq $app) { Write-Warning "Unknown project $n"; continue }
    $dir = Join-Path $root $app.dir

    if (-not (Test-Path (Join-Path $dir ".env"))) { Copy-Item (Join-Path $dir ".env.example") (Join-Path $dir ".env") }
    if ($app.index -and -not (Test-Path (Join-Path $dir $app.indexDir))) {
        Write-Host "[$n] building the vector index first (python -m $($app.index)) ..."
        Push-Location $dir; & $python -m @($app.index -split " "); Pop-Location
    }
    New-Item -ItemType Directory -Force (Join-Path $dir "logs") | Out-Null

    if (Test-Port $app.apiPort) {
        Write-Host "[$n] API already running on :$($app.apiPort)"
    } else {
        Start-Process -FilePath $python -WorkingDirectory $dir -WindowStyle Hidden `
            -ArgumentList "-m", "uvicorn", $app.api, "--port", $app.apiPort `
            -RedirectStandardOutput (Join-Path $dir "logs\api.out.log") -RedirectStandardError (Join-Path $dir "logs\api.log")
    }
    if ($app.uiPort) {
        if (Test-Port $app.uiPort) {
            Write-Host "[$n] UI already running on :$($app.uiPort)"
        } else {
            Start-Process -FilePath $python -WorkingDirectory $dir -WindowStyle Hidden `
                -ArgumentList "-m", "streamlit", "run", "ui/streamlit_app.py", "--server.port", $app.uiPort, "--server.headless", "true", "--browser.gatherUsageStats", "false" `
                -RedirectStandardOutput (Join-Path $dir "logs\ui.out.log") -RedirectStandardError (Join-Path $dir "logs\ui.log")
        }
        $urls = "API http://localhost:$($app.apiPort)/docs   UI http://localhost:$($app.uiPort)"
    } else {
        $urls = "API + chat UI http://localhost:$($app.apiPort)"
    }
    Write-Host ("[{0}] {1,-36} {2}" -f $n, $app.dir, $urls)
}
Write-Host "Starting up (first request can take 10-30 s while models and indexes load). Check: .\scripts\status.ps1"
