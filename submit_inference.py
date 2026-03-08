"""
Submit a SageMaker Processing Job for SLM inference.
Loads base model + LoRA adapter, runs predictions on test set, uploads results to S3.

Usage:
  python3 submit_inference.py \
    --role arn:aws:iam::ACCOUNT_ID:role/SageMakerRole \
    --bucket your-telco-llm-bucket \
    --model_id mistralai/Mistral-Nemo-Base-2407 \
    [--instance_type ml.g5.2xlarge] \
    [--hf_token HF_TOKEN]
"""
import argparse, time, boto3, sagemaker
from sagemaker.processing import ScriptProcessor, ProcessingInput, ProcessingOutput

# Same DLC as training — has transformers, peft, bitsandbytes, torch
PROCESSING_IMAGE_URI = (
    "763104351884.dkr.ecr.{region}.amazonaws.com/"
    "huggingface-pytorch-training:2.8.0-transformers4.56.2-gpu-py312-cu129-ubuntu22.04"
)

MODEL_DEFAULTS = {
    "mistralai/Mistral-Nemo-Base-2407": {"instance_type": "ml.g5.2xlarge"},
    "Qwen/Qwen3-14B":                   {"instance_type": "ml.g5.12xlarge"},
    "google/gemma-3-12b-pt":            {"instance_type": "ml.g5.2xlarge"},
}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--role",          required=True,  help="SageMaker IAM role ARN")
    parser.add_argument("--bucket",        required=True,  help="S3 bucket name")
    parser.add_argument("--region",        default="us-east-1")
    parser.add_argument("--model_id",      default="mistralai/Mistral-Nemo-Base-2407")
    parser.add_argument("--instance_type", default=None,   help="Override default instance type")
    parser.add_argument("--hf_token",      default=None,   help="HF token for gated models (Gemma)")
    parser.add_argument("--wait",          action="store_true", help="Block until job completes")
    return parser.parse_args()


def poll_job(sm_client, job_name, interval=60):
    """Poll processing job status until terminal state."""
    print(f"\nPolling job: {job_name}")
    while True:
        resp = sm_client.describe_processing_job(ProcessingJobName=job_name)
        status = resp["ProcessingJobStatus"]
        print(f"  [{time.strftime('%H:%M:%S')}] Status: {status}")
        if status in ("Completed", "Failed", "Stopped"):
            if status == "Failed":
                print(f"  Failure reason: {resp.get('FailureReason', 'N/A')}")
            return status
        time.sleep(interval)


def main():
    args = parse_args()

    defaults = MODEL_DEFAULTS.get(args.model_id, {"instance_type": "ml.g5.2xlarge"})
    instance_type = args.instance_type or defaults["instance_type"]

    # Derive model slug for naming
    slug = args.model_id.split("/")[-1].lower().replace(".", "-").replace("_", "-")
    job_name = f"telco-rca-infer-{slug[:20]}-{int(time.time())}"
    output_filename = f"preds_{slug}_slm.jsonl"

    boto_session = boto3.Session(region_name=args.region)
    sm_session = sagemaker.Session(boto_session=boto_session)
    sm_client = boto_session.client("sagemaker")

    # The adapter is stored under the training job output path
    adapter_s3_uri = f"s3://{args.bucket}/output/{slug}/"

    env = {}
    if args.hf_token:
        env["HF_TOKEN"] = args.hf_token

    processor = ScriptProcessor(
        role=args.role,
        image_uri=PROCESSING_IMAGE_URI.format(region=args.region),
        instance_type=instance_type,
        instance_count=1,
        command=["python3"],
        sagemaker_session=sm_session,
        env=env,
        base_job_name=f"telco-rca-infer-{slug[:20]}",
    )

    processor.run(
        code="src/inference_slm.py",
        source_dir="./src",
        inputs=[
            ProcessingInput(
                source=f"s3://{args.bucket}/data/test.jsonl",
                destination="/opt/ml/processing/input/test",
                input_name="test",
            ),
            ProcessingInput(
                source=adapter_s3_uri,
                destination="/opt/ml/processing/input/adapter",
                input_name="adapter",
            ),
        ],
        outputs=[
            ProcessingOutput(
                source="/opt/ml/processing/output",
                destination=f"s3://{args.bucket}/results/",
                output_name="predictions",
            ),
        ],
        arguments=[
            "--model_id", args.model_id,
            "--adapter_dir", "/opt/ml/processing/input/adapter/adapter",
            "--test_file", "/opt/ml/processing/input/test/test.jsonl",
            "--output_file", f"/opt/ml/processing/output/{output_filename}",
        ],
        wait=False,
    )

    actual_job_name = processor.latest_job.name
    console_url = (
        f"https://console.aws.amazon.com/sagemaker/home?region={args.region}"
        f"#/processing-jobs/{actual_job_name}"
    )
    print(f"\nJob submitted : {actual_job_name}")
    print(f"Instance      : {instance_type}")
    print(f"Model         : {args.model_id}")
    print(f"Adapter       : {adapter_s3_uri}")
    print(f"Output        : s3://{args.bucket}/results/{output_filename}")
    print(f"Console       : {console_url}")
    print(f"\nPoll status   : aws sagemaker describe-processing-job --processing-job-name {actual_job_name} --query ProcessingJobStatus --output text")

    if args.wait:
        final = poll_job(sm_client, actual_job_name)
        print(f"\nFinal status: {final}")


if __name__ == "__main__":
    main()
