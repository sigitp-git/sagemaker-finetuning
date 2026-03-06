"""
Synthetic 3GPP RCA data generation via Amazon Bedrock (Nova Pro).
Generates 1,300 train + 1,000 test labeled examples across 8 failure types.
Output: data/train.jsonl, data/test.jsonl
"""

import boto3
import json
import random
import time
import argparse
from pathlib import Path

REGION = "us-east-1"
MODEL_ID = "amazon.nova-pro-v1:0"

FAILURE_TYPES = [
    "core_network_failure",
    "authentication_failure",
    "normal",
    "handover_failure",
    "congestion",
    "qos_violation",
    "transport_jitter",
    "radio_failure",
]

# Per-failure prompt templates to guide realistic log generation
FAILURE_PROMPTS = {
    "core_network_failure": (
        "Generate a synthetic 3GPP NAS/NGAP signaling log for a 5G SA core showing a UPF "
        "degradation cascade failure. The AMF loses N11 interface to SMF, PDU sessions drop. "
        "Include sympathetic noise: heartbeat timeouts, keepalive retries, spurious PFCP "
        "session modification attempts."
    ),
    "authentication_failure": (
        "Generate a synthetic 3GPP NAS signaling log showing a 5G AKA authentication failure. "
        "UE sends Registration Request, AMF triggers Authentication Request, UE responds with "
        "wrong RES*, AMF sends Authentication Reject (cause 21). Include retries and "
        "sympathetic noise: duplicate NAS messages, timer T3560 expiry."
    ),
    "normal": (
        "Generate a synthetic 3GPP NAS/NGAP/RRC signaling log showing a completely successful "
        "5G SA registration and PDU session establishment. UE attaches, authenticates, gets IP, "
        "data flows normally. Include normal keepalives and periodic TAU."
    ),
    "handover_failure": (
        "Generate a synthetic 3GPP NGAP/Xn signaling log showing an Xn-based handover failure "
        "between two gNBs. Handover Request is sent but target gNB responds with Handover "
        "Failure (cause: radio-network / no-radio-resources-available). Include sympathetic "
        "noise: RRC measurement reports, A3 event triggers."
    ),
    "congestion": (
        "Generate a synthetic 3GPP NAS/NGAP signaling log showing AMF overload / congestion. "
        "AMF sends Overload Start with reduction percentage. UEs receive Registration Reject "
        "cause #22 (congestion). Include sympathetic noise: back-off timer T3346, repeated "
        "registration attempts."
    ),
    "qos_violation": (
        "Generate a synthetic 3GPP NAS/NGAP/N4 signaling log showing a QoS policy violation. "
        "SMF installs a GBR QoS flow but UPF reports the guaranteed bitrate cannot be met. "
        "PCF triggers policy update. Include sympathetic noise: PFCP session modification, "
        "N1 PDU Session Modification Command."
    ),
    "transport_jitter": (
        "Generate a synthetic 3GPP F1/NG/Xn interface log showing high transport jitter "
        "between gNB-DU and gNB-CU causing PDCP reordering timeouts and RLC retransmissions. "
        "Include sympathetic noise: HARQ NACK bursts, RLC status PDUs, spurious RRC "
        "RRCReconfiguration."
    ),
    "radio_failure": (
        "Generate a synthetic 3GPP RRC/NGAP signaling log showing radio link failure (RLF). "
        "UE detects T310 expiry, sends RRC Setup Request after RLF. gNB triggers UE Context "
        "Release. Include sympathetic noise: CQI degradation reports, beam failure recovery "
        "attempts, spurious measurement reports."
    ),
}


def build_prompt(failure_type: str) -> str:
    scenario = FAILURE_PROMPTS[failure_type]
    return f"""{scenario}

Output ONLY a valid JSON object on a single line with exactly two keys:
- "log": a realistic multi-line 3GPP signaling log string (use \\n for newlines), 150-300 words
- "root_cause": a JSON array containing exactly one string from this list: {json.dumps(FAILURE_TYPES)}

The root_cause array must contain: ["{failure_type}"]

Example format: {{"log": "2024-01-15 10:23:41.123 [AMF] ...", "root_cause": ["{failure_type}"]}}

Respond with ONLY the JSON object, no explanation, no markdown."""


def generate_example(bedrock, failure_type: str, max_retries: int = 3) -> dict | None:
    prompt = build_prompt(failure_type)
    for attempt in range(max_retries):
        try:
            response = bedrock.invoke_model(
                modelId=MODEL_ID,
                body=json.dumps({
                    "messages": [{"role": "user", "content": [{"text": prompt}]}],
                    "inferenceConfig": {"maxTokens": 1024, "temperature": 0.8},
                }),
                contentType="application/json",
                accept="application/json",
            )
            body = json.loads(response["body"].read())
            text = body["output"]["message"]["content"][0]["text"].strip()

            # Strip markdown code fences if present
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()

            example = json.loads(text)
            # Validate structure
            assert "log" in example and "root_cause" in example
            assert isinstance(example["root_cause"], list)
            assert len(example["root_cause"]) > 0
            return example

        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                print(f"  [WARN] Failed after {max_retries} attempts for {failure_type}: {e}")
                return None


def generate_dataset(n: int, output_path: str, seed: int = 42):
    random.seed(seed)
    bedrock = boto3.client("bedrock-runtime", region_name=REGION)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Distribute evenly across 8 failure types, shuffle
    per_class = n // len(FAILURE_TYPES)
    remainder = n % len(FAILURE_TYPES)
    schedule = FAILURE_TYPES * per_class + FAILURE_TYPES[:remainder]
    random.shuffle(schedule)

    written = 0
    skipped = 0
    with open(output_path, "w") as f:
        for i, failure_type in enumerate(schedule):
            example = generate_example(bedrock, failure_type)
            if example:
                f.write(json.dumps(example) + "\n")
                written += 1
            else:
                skipped += 1

            if (i + 1) % 50 == 0:
                print(f"  Progress: {i+1}/{n} | written={written} skipped={skipped}")

            # Respect Bedrock rate limits (~60 RPM for Nova Pro)
            time.sleep(1.1)

    print(f"Done: {written} examples written to {output_path} ({skipped} skipped)")
    return written


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-size", type=int, default=1300)
    parser.add_argument("--test-size", type=int, default=1000)
    parser.add_argument("--train-out", default="data/train.jsonl")
    parser.add_argument("--test-out", default="data/test.jsonl")
    parser.add_argument("--only", choices=["train", "test"], default=None,
                        help="Generate only train or test split")
    args = parser.parse_args()

    if args.only != "test":
        print(f"Generating {args.train_size} training examples...")
        generate_dataset(args.train_size, args.train_out, seed=42)

    if args.only != "train":
        print(f"Generating {args.test_size} test examples...")
        generate_dataset(args.test_size, args.test_out, seed=99)
