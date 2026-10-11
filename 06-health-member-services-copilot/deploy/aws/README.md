# Deploying to AWS (Amazon Bedrock + Bedrock AgentCore Runtime)

The local and AWS deployments run **the same code**. The switch is configuration only:

| Concern | Local | AWS |
|---|---|---|
| LLM | Ollama `llama3.2` | Bedrock: Claude (Converse API) |
| Embeddings | Ollama `nomic-embed-text` (768d) | Bedrock: Titan Text Embeddings V2 (1024d) |
| Vector store | Chroma (on disk) | Chroma baked into the image, **or** Bedrock Knowledge Base (`VECTOR_BACKEND=bedrock_kb`) |
| Guardrails | Local rules | Local rules + Bedrock Guardrails (ApplyGuardrail) |
| Hosting | uvicorn / docker compose | Bedrock AgentCore Runtime (arm64 container, `/invocations` + `/ping` on 8080) |
| Memory | In-memory / SQLite checkpointer | Per-session microVM memory; durable option: DynamoDB/AgentCore Memory |
| Logs | stdout JSON | CloudWatch Logs (`/aws/bedrock-agentcore/runtimes/...`) |

## 0. Prerequisites
1. An AWS account. In the Bedrock console under **Model access**, enable a Claude model and **Titan Text Embeddings V2** in your region (for example `us-east-1`).
2. AWS CLI v2 (`aws configure` or SSO), Docker with `buildx`, and Python 3.11+ with `pip install -r requirements.txt`.
3. Choose the Claude inference profile ID available to you. List the options with
   `aws bedrock list-inference-profiles --region us-east-1`
   and set `BEDROCK_CHAT_MODEL_ID` (or pass `--chat-model`).

## 1. One-command deploy
```bash
export AWS_REGION=us-east-1
bash deploy/aws/deploy.sh
```
The script runs these steps:
1. **Unit tests**: the quality gate.
2. **Bedrock Guardrail** (`create_guardrail.py`): creates content filters, a prompt-attack filter, denied topics (medical diagnosis, investment/legal advice), PII block/anonymise, and contextual grounding, then publishes a version.
3. **Vector index**: re-embeds the documents with Titan (`LLM_PROVIDER=bedrock python -m app.ingest --reset`). The index is written to `chroma_db/` and baked into the image.
4. **IAM role**: creates `EvergreenAgentCoreRuntimeRole` with least-privilege access (Bedrock invoke, ApplyGuardrail, ECR pull, logs).
5. **Image**: builds a `linux/arm64` image and pushes it to ECR (with scan on push).
6. **AgentCore Runtime** (`deploy_agentcore.py`): creates or updates the runtime with environment variables pointing to Bedrock and the guardrail.

## 2. Smoke test
```bash
python deploy/aws/invoke_agentcore.py --arn <AGENT_RUNTIME_ARN> \
  --prompt "Why was claim CLM-10002 denied?" --member-id M1001
```

## 3. Evaluate in the cloud (before promoting)
```bash
LLM_PROVIDER=bedrock RELEVANCE_THRESHOLD=0.35 EVAL_JUDGE_PROVIDER=bedrock python -m eval.run_eval
```
Re-calibrate `RELEVANCE_THRESHOLD` for Titan. Scores are distributed differently from nomic-embed-text, so check `retrieval_hit_rate` in the report.

## Alternative A: AgentCore starter toolkit (fastest path)
```bash
pip install bedrock-agentcore-starter-toolkit
agentcore configure --entrypoint app/agentcore_entrypoint.py --region us-east-1
agentcore launch --env LLM_PROVIDER=bedrock --env BEDROCK_GUARDRAIL_ID=<id> --env BEDROCK_GUARDRAIL_VERSION=1
agentcore invoke '{"prompt": "What is the Gold PPO deductible?", "member_id": "M1001"}'
```

## Alternative B: Bedrock Knowledge Base instead of Chroma
1. Upload `data/policies/*.md` to S3.
2. Create a Knowledge Base (Titan V2 embeddings, OpenSearch Serverless) and sync it.
3. Deploy with `--kb-id <KB_ID>`, which sets `VECTOR_BACKEND=bedrock_kb`.

This gives managed ingestion and sync for large or changing corpora, with no index inside the image.

## Alternative C: ECS Fargate / App Runner
The same image serves `/chat` and the UI on port 8080. Put it behind an ALB with Cognito/OIDC auth. Derive `member_id` from the verified JWT, never from the request body.

## Production hardening checklist
- [ ] Get `member_id` from an AgentCore inbound authorizer (Cognito/OIDC JWT), not from the payload.
- [ ] Use a durable checkpointer (DynamoDB / AgentCore Memory) for multi-instance conversation memory.
- [ ] Connect the claims tool to the real claims API through AgentCore Gateway, with per-member scoping.
- [ ] Add CloudWatch alarms on p95 latency, 5xx, guardrail intervention rate, and groundedness-fail rate.
- [ ] Turn on LangSmith or CloudWatch GenAI observability tracing, with PII redaction already applied at the edge.
- [ ] Run the evaluation gate on every PR. Use a canary alias for new runtime versions.
- [ ] Sign a BAA, use HIPAA-eligible services only, KMS-encrypt data at rest, and use VPC network mode for PHI.
