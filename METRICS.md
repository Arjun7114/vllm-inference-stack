# Metrics & Benchmarks

Real numbers captured while building this stack. These are the figures that back
up résumé claims and the README's performance section. Filled in phase by phase.

> All numbers are from *my own* runs on the hardware noted — not vendor claims.

---

## Environment

| Item | Value |
|------|-------|
| GPU | RTX PRO 4500 Blackwell, 32 GB VRAM (RunPod Community Cloud) |
| GPU cost | ~$0.72/hr |
| Model | mistralai/Mistral-7B-Instruct-v0.3 |
| Precision | bfloat16 (auto-selected) |
| vLLM version | 0.28.0 |
| Container image | runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404 |
| CUDA (driver) | 13.0 (driver 580.173.02) |

---

## Phase 1 — Serving

| Metric | Value | Notes |
|--------|-------|-------|
| Weights on GPU | ~13.9 GiB | model itself |
| KV cache reserved | ~14.0 GiB | PagedAttention working memory |
| Peak activation + CUDA graphs | ~0.7 GiB | |
| Total VRAM in use | ~28 GiB / 32 GiB | why 24 GB would've been tight |
| Warmup / compile time | ~31 s | 15.5 s of it compilation |
| `--gpu-memory-utilization` | 0.90 | |
| `--max-model-len` | 8192 | confirmed via /v1/models |
| First chat request | 200 OK | 16 prompt + 43 completion = 59 tokens |

**Troubleshooting note:** FlashInfer sampler failed an sm75 arch check on the
Blackwell GPU; resolved with `VLLM_USE_FLASHINFER_SAMPLER=0` (native sampling
path). Documented in serving/NOTES.md.

---

## Phase 3 — Streaming (single request)

| Metric | Value |
|--------|-------|
| Time to first token (TTFT) | _ms_ |
| Tokens/sec (generation) | _tok/s_ |

---

## Phase 7 — Observability (from vLLM /metrics)

| Metric | Value |
|--------|-------|
| KV-cache utilization (steady load) | _%_ |
| Running vs waiting requests (peak) | _n / n_ |

---

## Phase 8 — Load test  (resume headline numbers)

Tool: _k6 / Locust_ · Concurrency: _N_ · Duration: _e.g. 2 min_

| Metric | Value |
|--------|-------|
| Requests/sec (sustained) | _req/s_ |
| p50 latency | _ms_ |
| p95 latency | _ms_ |
| p99 latency | _ms_ |
| Aggregate tokens/sec | _tok/s_ |
| Error rate | _%_ |

**Résumé-ready sentence (fill in once measured):**
> Served Mistral-7B on a single 24 GB GPU at ~___ req/s with p95 latency of
> ___ ms and ___ tokens/sec aggregate throughput, packaged with Docker and
> observed via Prometheus + Grafana.

---

## Phase 9 — AWS deployment

| Metric | Value |
|--------|-------|
| Instance type | _e.g. g5.xlarge_ |
| On-demand cost | _$__/hr_ |
| Deploy time (image -> serving) | _min:sec_ |
| Ran unchanged from local? | _yes/no + notes_ |
