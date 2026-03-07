# Fixes

## [2026-03-07] Mistral-Nemo LoRA shape mismatch

**Job:** `telco-rca-ministral-3-14b-2026-03-07-01-37-02-420`  
**Status:** Failed after ~7 min (exit code 1)

### Error

```
ValueError: Trying to set a tensor of shape torch.Size([1024, 5120]) in "weight"
(which has shape torch.Size([1280, 5120])), this looks incorrect.
```

### Root Cause

`Mistral-Nemo-Base-2407` uses Grouped Query Attention (GQA) where `v_proj` has output
dimension `num_kv_heads × head_dim = 10 × 128 = 1280`, not the full `num_heads × head_dim`
you'd expect from standard MHA. The original LoRA config only targeted `["q_proj", "v_proj"]`,
which caused PEFT to misalign adapter shapes when initializing against the GQA projection layers.

### Fix

Added `k_proj` and `o_proj` to the target modules for Mistral-Nemo in `LORA_CONFIGS` (`train.py`):

```python
# Before
"mistralai/Mistral-Nemo-Base-2407": (16, 32, ["q_proj", "v_proj"]),

# After
"mistralai/Mistral-Nemo-Base-2407": (16, 32, ["q_proj", "k_proj", "v_proj", "o_proj"]),
```

Targeting all four projection layers is the standard safe approach for GQA models — it lets
PEFT correctly infer shapes across all attention projections regardless of KV head count.
