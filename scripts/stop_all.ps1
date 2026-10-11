# Stop the APIs and UIs started by start_all.ps1 (ports from projects.ps1).
#   .\scripts\stop_all.ps1                  # all
#   .\scripts\stop_all.ps1 -Projects 03     # only project 03
param([string[]]$Projects = @("01", "02", "03", "04", "05", "06", "07", "08"))

. (Join-Path $PSScriptRoot "projects.ps1")
foreach ($n in $Projects | ForEach-Object { "{0:D2}" -f [int]"$_" }) {   # "-Projects 7,08" and "07" both work
    $app = $PortfolioProjects[$n]
    if ($null -eq $app) { Write-Warning "Unknown project $n"; continue }
    foreach ($port in @($app.apiPort, $app.uiPort) | Where-Object { $_ }) {
        $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
        foreach ($procId in ($conns | Select-Object -ExpandProperty OwningProcess -Unique)) {
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
            Write-Host "stopped :$port (pid $procId)"
        }
    }
}
