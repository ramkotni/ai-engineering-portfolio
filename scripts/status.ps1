# Show which project APIs and UIs are up, with each API's /health response.
$names = @{ "01" = "payment-ops"; "02" = "robotics-fleet"; "03" = "supply-chain-kb"; "04" = "feasibility-ml"; "05" = "plant-assist" }
foreach ($n in "01", "02", "03", "04", "05") {
    $apiPort = 8000 + [int]$n
    $uiPort = 8500 + [int]$n
    try { $health = (Invoke-RestMethod "http://localhost:$apiPort/health" -TimeoutSec 3).status } catch { $health = "down" }
    try { $ui = if ((Invoke-WebRequest "http://localhost:$uiPort" -UseBasicParsing -TimeoutSec 3).StatusCode -eq 200) { "up" } } catch { $ui = "down" }
    "{0} {1,-16} API :{2} {3,-5} UI :{4} {5}" -f $n, $names[$n], $apiPort, $health, $uiPort, $ui
}
