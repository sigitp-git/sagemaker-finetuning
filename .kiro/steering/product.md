# Product

This repository is a step-by-step guide for a fine-tuning benchmark that compares fine-tuned 14B Small Language Models (SLMs) against frontier foundation models on automated Root Cause Analysis (RCA) of 3GPP protocol logs in 5G Standalone core networks.

## Purpose

- Fine-tune SLMs (Ministral 3 14B, Qwen3-14B, Gemma 3 12B) using LoRA/QLoRA on synthetic 3GPP signaling data
- Evaluate fine-tuned SLMs against frontier models (Claude, Amazon Nova Pro) via Amazon Bedrock
- Demonstrate that domain-specific fine-tuned SLMs can match or exceed frontier model accuracy at a fraction of the inference cost

## Target Users

ML engineers and telecom researchers who want to run or extend this benchmark using AWS managed services.

## Key Outcomes

- Trained LoRA adapters for 3GPP RCA classification across 8 failure types
- Evaluation metrics: F1, Precision, Recall, Exact Match
- Deployment patterns for edge/on-premise telco environments
- HTML report and JavaScript-based PPT presentation (pptxgenjs) generated from `results.json`
