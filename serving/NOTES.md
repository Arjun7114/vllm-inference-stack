# Serving Notes — Phase 1

How the model is served, what every flag means, and the real numbers observed on
the GPU. This is the "understand what you did" record for the serving layer.

## The command

```bash
VLLM_USE_FLASHINFER_SAMPLER=0 \
vllm serve mistralai/Mistral-7B-Instruct-v0.3 \
  --port 8000 \
  --gpu-memory-utilization 0.90 \
  --max-model-len 8192
```

vLLM reads the Hugging Face token from the `HF_TOKEN` environment variable
automatically to authenticate the model download. The token is never typed into
this command or any file — on RunPod it is injected from an encrypted Secret via
`{{ RUNPOD_SECRET_HF_TOKEN }}`.

## What each flag does

- **`vllm serve <model>`** — starts vLLM's OpenAI-compatible API server and loads
  the named model. Weights are pulled from Hugging Face on first run and cached.
- **`--port 8000`** — the port the API listens on. Must match the port exposed on
  the pod so the endpoint is reachable.
- **`--gpu-memory-utilization 0.90`** — lets vLLM use up to 90% of GPU VRAM. vLLM
  pre-reserves a large block for the **KV cache** (the PagedAttention store that
  holds attention state for in-flight requests). Higher = more room for batching
  and longer contexts; leave headroom (0.90, not 1.0) to avoid an out-of-memory
  crash.
- **`--max-model-len 8192`** — caps context length at 8192 tokens. This directly
  bounds how much KV-cache memory a single request can consume. Mistral supports
  up to 32k, but capping keeps memory predictable and is plenty for a chat app.

## Key concept: where the VRAM goes

Observed on startup (RTX PRO 4500, 32 GB):

- Weights + non-torch: **~13.9 GiB** (the model itself)
- KV cache reserved: **~14.0 GiB** (PagedAttention working memory)
- Peak activation + CUDA graphs: **~0.7 GiB**

So ~13.9 GB weights + ~14 GB KV cache ≈ 28 GB in use. This is exactly why a 24 GB
card would have been tight and 32 GB gave comfortable headroom — and why the
`--gpu-memory-utilization` and `--max-model-len` flags matter: together they
decide how much of that budget the KV cache is allowed to claim.

Precision was auto-selected as **bfloat16**. Warmup/compile took ~31 s.

## Troubleshooting: FlashInfer on Blackwell

First launch failed at the warmup step with:

```
RuntimeError: FlashInfer requires GPUs with sm75 or higher
```

Cause: a compatibility wrinkle between the brand-new Blackwell GPU and vLLM's
FlashInfer sampler backend (the arch check misfired — the card is newer than
sm75, not older). Fix: disable the FlashInfer sampler and fall back to vLLM's
native PyTorch sampling path:

```bash
VLLM_USE_FLASHINFER_SAMPLER=0
```

Functionally identical output; only the sampling kernel differs. Lesson: newer
hardware can hit backend-detection edge cases — the fix is to select a compatible
backend, not to change hardware.

## Verifying the server

List the served model:

```bash
curl http://localhost:8000/v1/models
```

Send a chat request (OpenAI-compatible shape — any OpenAI client works unchanged):

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistralai/Mistral-7B-Instruct-v0.3",
    "messages": [{"role": "user", "content": "In one sentence, what is an LLM inference server?"}],
    "max_tokens": 60
  }'
```

The generated text is in `choices[0].message.content`; token counts are in the
`usage` block.
