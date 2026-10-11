"""Create or update the Bedrock AgentCore Runtime from an ECR image.

    python deploy/aws/deploy_agentcore.py \
        --image 123456789012.dkr.ecr.us-east-1.amazonaws.com/evergreen-assist:v1 \
        --role-arn arn:aws:iam::123456789012:role/EvergreenAgentCoreRuntimeRole \
        --guardrail-id abc123 --guardrail-version 1
"""
from __future__ import annotations

import argparse
import time

import boto3

RUNTIME_NAME = "evergreen_member_assist"  # pattern: [a-zA-Z][a-zA-Z0-9_]{0,47}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--image", required=True)
    p.add_argument("--role-arn", required=True)
    p.add_argument("--region", default="us-east-1")
    p.add_argument("--chat-model", default="us.anthropic.claude-sonnet-4-5-20250929-v1:0")
    p.add_argument("--embed-model", default="amazon.titan-embed-text-v2:0")
    p.add_argument("--guardrail-id")
    p.add_argument("--guardrail-version", default="1")
    p.add_argument("--kb-id", help="use Bedrock Knowledge Base instead of the in-image Chroma index")
    args = p.parse_args()

    env = {
        "APP_ENV": "aws",
        "LLM_PROVIDER": "bedrock",
        "AWS_REGION": args.region,
        "BEDROCK_CHAT_MODEL_ID": args.chat_model,
        "BEDROCK_EMBED_MODEL_ID": args.embed_model,
        "VECTOR_BACKEND": "bedrock_kb" if args.kb_id else "chroma",
        "RELEVANCE_THRESHOLD": "0.35",  # re-calibrate for Titan embeddings with eval/run_eval.py
        "LOG_LEVEL": "INFO",
        "GROUNDEDNESS_MODE": "both",  # numeric + Claude fact-checker
    }
    if args.kb_id:
        env["BEDROCK_KB_ID"] = args.kb_id
    if args.guardrail_id:
        env["BEDROCK_GUARDRAIL_ID"] = args.guardrail_id
        env["BEDROCK_GUARDRAIL_VERSION"] = args.guardrail_version

    ctl = boto3.client("bedrock-agentcore-control", region_name=args.region)
    common = dict(
        agentRuntimeArtifact={"containerConfiguration": {"containerUri": args.image}},
        roleArn=args.role_arn,
        networkConfiguration={"networkMode": "PUBLIC"},
        protocolConfiguration={"serverProtocol": "HTTP"},
        environmentVariables=env,
    )

    existing = next(
        (r for r in ctl.list_agent_runtimes().get("agentRuntimes", []) if r["agentRuntimeName"] == RUNTIME_NAME), None
    )
    if existing:
        resp = ctl.update_agent_runtime(agentRuntimeId=existing["agentRuntimeId"], **common)
        print("Updating runtime", existing["agentRuntimeId"])
    else:
        resp = ctl.create_agent_runtime(agentRuntimeName=RUNTIME_NAME, description="Evergreen Member Assist", **common)
        print("Creating runtime", resp["agentRuntimeId"])

    runtime_id = resp["agentRuntimeId"]
    for _ in range(60):
        status = ctl.get_agent_runtime(agentRuntimeId=runtime_id)["status"]
        print("  status:", status)
        if status in ("READY", "CREATE_FAILED", "UPDATE_FAILED"):
            break
        time.sleep(10)
    print("\nAGENT_RUNTIME_ARN=" + resp["agentRuntimeArn"])


if __name__ == "__main__":
    main()
