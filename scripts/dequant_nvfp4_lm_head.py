"""Replace a ModelOpt NVFP4 lm_head with its exact BF16 dequantization.

vLLM's Qwen3_5 ParallelLMHead is never quantized, so it rejects lm_head.input_scale
and friends. Usage: dequant_nvfp4_lm_head.py MODEL_DIR
"""
import json
import os
import sys

import torch
from safetensors import safe_open
from safetensors.torch import save_file

E2M1 = torch.tensor([0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0], dtype=torch.float32)


def dequant(packed, sf, gscale, block=16):
    m, pk = packed.shape
    low, high = packed & 0x0F, (packed & 0xF0) >> 4
    nib = torch.stack((low, high), dim=-1).reshape(m, pk * 2)  # low nibble first
    vals = E2M1[(nib & 0x07).long()] * torch.where((nib & 0x08).bool(), -1.0, 1.0)
    vals = vals.reshape(m, -1, block) * (sf.view(torch.float8_e4m3fn).float() * gscale).unsqueeze(-1)
    return vals.reshape(m, pk * 2).to(torch.bfloat16)


d = sys.argv[1]
idx_path = os.path.join(d, "model.safetensors.index.json")
idx = json.load(open(idx_path))
shard = idx["weight_map"]["lm_head.weight"]
src = os.path.join(d, shard)

tensors = {}
with safe_open(src, "pt") as f:
    meta = f.metadata()
    for k in f.keys():
        if not k.startswith("lm_head."):
            tensors[k] = f.get_tensor(k)
    w = dequant(f.get_tensor("lm_head.weight"), f.get_tensor("lm_head.weight_scale"),
                f.get_tensor("lm_head.weight_scale_2").float())
tensors["lm_head.weight"] = w
print("lm_head bf16", tuple(w.shape), "absmax", w.abs().max().item(), "row-norm mean", w.float().norm(dim=1).mean().item())

tmp = src + ".tmp"
save_file(tensors, tmp, metadata=meta)
os.rename(src, src + ".orig-nvfp4-lmhead")
os.rename(tmp, src)

for k in ("lm_head.input_scale", "lm_head.weight_scale", "lm_head.weight_scale_2"):
    idx["weight_map"].pop(k, None)
json.dump(idx, open(idx_path, "w"), indent=2)

cfg_path = os.path.join(d, "config.json")
cfg = json.load(open(cfg_path))
ign = cfg["quantization_config"]["ignore"]
if "lm_head" not in ign:
    ign.append("lm_head")
json.dump(cfg, open(cfg_path, "w"), indent=2)

hq_path = os.path.join(d, "hf_quant_config.json")
hq = json.load(open(hq_path))
ex = hq["quantization"]["exclude_modules"]
if "lm_head" not in ex:
    ex.append("lm_head")
json.dump(hq, open(hq_path, "w"), indent=4)
print("done:", shard)
