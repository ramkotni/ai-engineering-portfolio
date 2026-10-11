# Stop the APIs (ports 8001-8005) and UIs (ports 8501-8505) started by start_all.ps1.
#   .\scripts\stop_all.ps1                  # all
#   .\scripts\stop_all.ps1 -Projects 03     # only project 03
param([string[]]$Projects = @("01", "02", "03", "04", "05"))

foreach ($n in $Projects) {
    foreach ($port in @((8000 + [int]$n), (8500 + [int]$n))) {
        $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
        foreach ($procId in ($conns | Select-Object -ExpandProperty OwningProcess -Unique)) {
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
            Write-Host "stopped :$port (pid $procId)"
        }
    }
}
