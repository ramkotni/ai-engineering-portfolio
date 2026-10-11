"""Smoke-test the deployed AgentCore Runtime.

    python deploy/aws/invoke_agentcore.py --arn <AGENT_RUNTIME_ARN> --prompt "What is the Gold PPO deductible?"
"""
from __future__ import annotations

import argparse
import json
import uuid

import boto3


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--arn", required=True)
    p.add_argument("--prompt", required=True)
    p.add_argument("--member-id", default="M1001")
    p.add_argument("--session-id", default=f"session-{uuid.uuid4()}")  # must be >= 33 chars
    p.add_argument("--region", default="us-east-1")
    args = p.parse_args()

    client = boto3.client("bedrock-agentcore", region_name=args.region)
    resp = client.invoke_agent_runtime(
        agentRuntimeArn=args.arn,
        runtimeSessionId=args.session_id,
        payload=json.dumps({"prompt": args.prompt, "member_id": args.member_id}).encode(),
        contentType="application/json",
        accept="application/json",
    )
    body = json.loads(resp["response"].read())
    print(json.dumps(body, indent=2))


if __name__ == "__main__":
    main()
