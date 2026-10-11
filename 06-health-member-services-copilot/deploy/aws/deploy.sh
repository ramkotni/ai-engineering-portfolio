#!/usr/bin/env bash
# End-to-end AWS deployment: guardrail -> Titan index -> arm64 image -> ECR -> AgentCore Runtime.
# Prereqs: AWS CLI v2 configured, Docker with buildx, Bedrock model access enabled
# (Claude + Titan Text Embeddings V2) in $AWS_REGION, and the venv activated.
set -euo pipefail

AWS_REGION="${AWS_REGION:-us-east-1}"
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
REPO="evergreen-assist"
TAG="${TAG:-$(date +%Y%m%d%H%M%S)}"
ROLE_NAME="EvergreenAgentCoreRuntimeRole"
IMAGE="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${REPO}:${TAG}"
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"

echo "==> 1/6 Quality gate: unit tests"
(cd "$ROOT" && python -m pytest -q)

echo "==> 2/6 Bedrock Guardrail"
GUARD_OUT="$(python "$HERE/create_guardrail.py" --region "$AWS_REGION")"
echo "$GUARD_OUT"
GUARDRAIL_ID="$(echo "$GUARD_OUT" | sed -n 's/^BEDROCK_GUARDRAIL_ID=//p')"
GUARDRAIL_VERSION="$(echo "$GUARD_OUT" | sed -n 's/^BEDROCK_GUARDRAIL_VERSION=//p')"

echo "==> 3/6 Build vector index with Titan embeddings (baked into the image)"
(cd "$ROOT" && LLM_PROVIDER=bedrock AWS_REGION="$AWS_REGION" python -m app.ingest --reset)

echo "==> 4/6 IAM execution role"
if ! aws iam get-role --role-name "$ROLE_NAME" >/dev/null 2>&1; then
  sed "s/ACCOUNT_ID/${ACCOUNT_ID}/g" "$HERE/iam-trust-policy.json" > /tmp/trust.json
  aws iam create-role --role-name "$ROLE_NAME" --assume-role-policy-document file:///tmp/trust.json >/dev/null
fi
sed -e "s/ACCOUNT_ID/${ACCOUNT_ID}/g" -e "s/REGION/${AWS_REGION}/g" "$HERE/iam-runtime-policy.json" > /tmp/policy.json
aws iam put-role-policy --role-name "$ROLE_NAME" --policy-name runtime --policy-document file:///tmp/policy.json
ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"

echo "==> 5/6 Build linux/arm64 image and push to ECR"
aws ecr describe-repositories --repository-names "$REPO" --region "$AWS_REGION" >/dev/null 2>&1 \
  || aws ecr create-repository --repository-name "$REPO" --region "$AWS_REGION" --image-scanning-configuration scanOnPush=true >/dev/null
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
docker buildx build --platform linux/arm64 -t "$IMAGE" --push "$ROOT"

echo "==> 6/6 Create/update AgentCore Runtime"
python "$HERE/deploy_agentcore.py" --image "$IMAGE" --role-arn "$ROLE_ARN" --region "$AWS_REGION" \
  --guardrail-id "$GUARDRAIL_ID" --guardrail-version "$GUARDRAIL_VERSION"

echo "Done. Smoke test:"
echo "  python $HERE/invoke_agentcore.py --arn <AGENT_RUNTIME_ARN> --prompt 'What is the Gold PPO deductible?'"
