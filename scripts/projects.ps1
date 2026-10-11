# Shared project table for start_all.ps1 / stop_all.ps1 / status.ps1.
# api     = uvicorn app (or a python -m module when apiModule is set); ui = Streamlit port, $null when the API serves its own UI
# index   = module that builds the vector index, run once if indexDir is missing
$PortfolioProjects = [ordered]@{
    "01" = @{ dir = "01-payment-ops-intelligence";         api = "payops.api:app";       apiPort = 8001; uiPort = 8501; index = "payops.ingest";       indexDir = ".chroma" }
    "02" = @{ dir = "02-robotics-fleet-assistant";         api = "fleetops.api:app";     apiPort = 8002; uiPort = 8502; index = "fleetops.ingest";     indexDir = ".chroma" }
    "03" = @{ dir = "03-supply-chain-knowledge-assistant"; api = "supplykb.api:app";     apiPort = 8003; uiPort = 8503; index = "supplykb.ingest";     indexDir = ".chroma" }
    "04" = @{ dir = "04-project-feasibility-ml";           api = "feasibility.api:app";  apiPort = 8004; uiPort = 8504; index = $null;                 indexDir = $null }
    "05" = @{ dir = "05-plant-assist";                     api = "plant_assist.api:app"; apiPort = 8005; uiPort = 8505; index = "plant_assist.ingest"; indexDir = ".chroma" }
    # 06 serves API + chat UI from one FastAPI app on 8080 (the Bedrock AgentCore Runtime port contract)
    "06" = @{ dir = "06-health-member-services-copilot";   api = "app.api:app";          apiPort = 8080; uiPort = $null; index = "app.ingest --reset"; indexDir = "chroma_db" }
    "07" = @{ dir = "07-healthcare-condition-briefing";    api = "medbrief.api:app";     apiPort = 8007; uiPort = 8507; index = "medbrief.ingest";     indexDir = ".chroma" }
    "08" = @{ dir = "08-finance-stock-briefing";           api = "stockbrief.api:app";   apiPort = 8008; uiPort = 8508; index = "stockbrief.ingest";   indexDir = ".chroma" }
}
