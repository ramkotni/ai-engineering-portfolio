"""Create (or version) the Amazon Bedrock Guardrail used by the assistant.

    python deploy/aws/create_guardrail.py --region us-east-1

Prints BEDROCK_GUARDRAIL_ID / BEDROCK_GUARDRAIL_VERSION to put in the runtime env.
"""
from __future__ import annotations

import argparse

import boto3

NAME = "evergreen-member-assist"
BLOCKED = (
    "I'm sorry, I can't help with that request. I can answer questions about your Evergreen "
    "plan benefits, claims, prior authorization, pharmacy coverage, and appeals."
)

CONFIG = dict(
    description="Member assistant guardrail: harmful content, prompt attacks, denied topics, PII, grounding",
    topicPolicyConfig={
        "topicsConfig": [
            {
                "name": "MedicalDiagnosis",
                "definition": "Diagnosing symptoms, recommending treatments, medications or dosages.",
                "examples": ["What medicine should I take for a headache?", "Do I have diabetes?"],
                "type": "DENY",
            },
            {
                "name": "InvestmentOrLegalAdvice",
                "definition": "Personalised investment, tax or legal advice.",
                "examples": ["Which stocks should I buy?", "Should I sue my doctor?"],
                "type": "DENY",
            },
        ]
    },
    contentPolicyConfig={
        "filtersConfig": [
            {"type": t, "inputStrength": "HIGH", "outputStrength": "HIGH"}
            for t in ("SEXUAL", "VIOLENCE", "HATE", "INSULTS", "MISCONDUCT")
        ]
        + [{"type": "PROMPT_ATTACK", "inputStrength": "HIGH", "outputStrength": "NONE"}]
    },
    sensitiveInformationPolicyConfig={
        "piiEntitiesConfig": [
            {"type": "US_SOCIAL_SECURITY_NUMBER", "action": "BLOCK"},
            {"type": "CREDIT_DEBIT_CARD_NUMBER", "action": "BLOCK"},
            {"type": "US_BANK_ACCOUNT_NUMBER", "action": "BLOCK"},
            {"type": "PASSWORD", "action": "BLOCK"},
            {"type": "EMAIL", "action": "ANONYMIZE"},
        ]
    },
    contextualGroundingPolicyConfig={
        "filtersConfig": [
            {"type": "GROUNDING", "threshold": 0.75},
            {"type": "RELEVANCE", "threshold": 0.5},
        ]
    },
    blockedInputMessaging=BLOCKED,
    blockedOutputsMessaging=BLOCKED,
)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--region", default="us-east-1")
    args = p.parse_args()
    bedrock = boto3.client("bedrock", region_name=args.region)

    existing = next((g for g in bedrock.list_guardrails()["guardrails"] if g["name"] == NAME), None)
    if existing:
        gid = existing["id"]
        bedrock.update_guardrail(guardrailIdentifier=gid, name=NAME, **CONFIG)
        print(f"Updated guardrail {gid}")
    else:
        gid = bedrock.create_guardrail(name=NAME, **CONFIG)["guardrailId"]
        print(f"Created guardrail {gid}")

    version = bedrock.create_guardrail_version(guardrailIdentifier=gid, description="release")["version"]
    print(f"\nBEDROCK_GUARDRAIL_ID={gid}\nBEDROCK_GUARDRAIL_VERSION={version}")


if __name__ == "__main__":
    main()
