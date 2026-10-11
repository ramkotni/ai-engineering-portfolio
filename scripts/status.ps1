# Show which project APIs and UIs are up, with each API's /health status.
. (Join-Path $PSScriptRoot "projects.ps1")
foreach ($n in $PortfolioProjects.Keys) {
    $app = $PortfolioProjects[$n]
    try { $health = (Invoke-RestMethod "http://localhost:$($app.apiPort)/health" -TimeoutSec 3).status } catch { $health = "down" }
    if ($app.uiPort) {
        try { $ui = if ((Invoke-WebRequest "http://localhost:$($app.uiPort)" -UseBasicParsing -TimeoutSec 3).StatusCode -eq 200) { "up" } } catch { $ui = "down" }
        $uiText = "UI :$($app.uiPort) $ui"
    } else {
        $uiText = "UI served by the API"
    }
    "{0} {1,-36} API :{2} {3,-5} {4}" -f $n, $app.dir, $app.apiPort, $health, $uiText
}
