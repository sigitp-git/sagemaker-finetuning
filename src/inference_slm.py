"""
SageMaker Processing Job entry point for SLM inference.
Loads base model + LoRA adapter in QLoRA 4-bit, runs predictions on test set.

Usage (SageMaker Processing):
  Invoked by submit_inference.py — not run directly.

Usage (local):
  python3 src/inference_slm.py \
    --model_id mistralai/Mistral-Nemo-Base-2407 \
    --adapter_dir ./adapters/mistral-nemo-base-2407 \
    --test_file data/test.jsonl \
    --output_file results/preds_mistral-nemo-base-2407_slm.jsonl
"""
import argparse, json, os, sys, torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel

PROMPT_TEMPLATE = (
    "### Instruction\n"
    "Analyze the following 3GPP signaling log and identify the root cause.\n\n"
    "### Log\n{log}\n\n"
    "### Root Cause\n"
)


def load_jsonl(path):
    with open(path) as f:
        return [json.loads(l) for l in f if l.strip()]


def parse_root_cause(text):
    """Extract root cause from generated text after '### Root Cause' marker."""
    # Add filter.py's directory to path for import
    sys.path.insert(0, os.path.dirname(__file__))
    from filter import extract_root_cause_from_text
    return extract_root_cause_from_text(text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_id", required=True)
    parser.add_argument("--adapter_dir", required=True, help="Path to LoRA adapter directory")
    parser.add_argument("--test_file", default="data/test.jsonl")
    parser.add_argument("--output_file", required=True)
    parser.add_argument("--max_new_tokens", type=int, default=64)
    parser.add_argument("--batch_size", type=int, default=4)
    args = parser.parse_args()

    # Authenticate with Hugging Face for gated models
    hf_token = os.environ.get("HF_TOKEN")
    if hf_token:
        from huggingface_hub import login
        login(token=hf_token)
        print("Authenticated with Hugging Face (gated model access)")

    print(f"Model: {args.model_id}")
    print(f"Adapter: {args.adapter_dir}")
    print(f"Test file: {args.test_file}")

    # Load base model in QLoRA 4-bit
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        args.model_id,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
        low_cpu_mem_usage=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(args.model_id, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "left"  # left-pad for batch generation

    # Merge LoRA adapter
    print(f"Loading adapter from {args.adapter_dir}")
    model = PeftModel.from_pretrained(model, args.adapter_dir)
    model.eval()

    # Load test data
    test_data = load_jsonl(args.test_file)
    print(f"Loaded {len(test_data)} test examples")

    # Run inference in batches
    results = []
    for i in range(0, len(test_data), args.batch_size):
        batch = test_data[i : i + args.batch_size]
        prompts = [PROMPT_TEMPLATE.format(log=ex["log"]) for ex in batch]

        inputs = tokenizer(prompts, return_tensors="pt", padding=True, truncation=True, max_length=960)
        inputs = {k: v.to(model.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=args.max_new_tokens,
                do_sample=False,
                temperature=1.0,
                pad_token_id=tokenizer.pad_token_id,
            )

        for j, output in enumerate(outputs):
            # Decode only the generated tokens (skip the prompt)
            prompt_len = inputs["input_ids"].shape[1]
            generated = tokenizer.decode(output[prompt_len:], skip_special_tokens=True).strip()
            root_cause = parse_root_cause(generated)
            results.append({"root_cause": root_cause, "output": generated})

        if (i // args.batch_size + 1) % 10 == 0 or i + args.batch_size >= len(test_data):
            print(f"  {min(i + args.batch_size, len(test_data))}/{len(test_data)} done")

    # Save predictions
    os.makedirs(os.path.dirname(args.output_file) or ".", exist_ok=True)
    with open(args.output_file, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")
    print(f"Saved {len(results)} predictions to {args.output_file}")


if __name__ == "__main__":
    main()
