# vLLM Inference Stack — A Self-Defending LLM Serving Platform

**An LLM inference platform that defends itself at runtime — and proves it with real numbers.**

A production-shaped serving stack for an open-source LLM (Mistral-7B on vLLM),
where every request passes inline through a security boundary, that defense is
measured against NVIDIA's own red-team scanner, and the whole thing runs as an
orchestrated, observable deployment on AWS GPU infrastructure.

> Not "I served an LLM." This is a serving platform with an inline security
> control, benchmarked, monitored, and deployed to real cloud GPU hardware.

---

## Results (measured on AWS EC2 g5.xlarge — NVIDIA A10G 24GB, Mistral-7B FP16)

### Performance (real load, through the full app layer)

| Concurrency | Throughput | Aggregate tokens/sec | p50 latency | p95 latency | Errors |
|-------------|-----------|----------------------|-------------|-------------|--------|
| 8           | 2.83 req/s | 219.8 tok/s          | 2816 ms     | 4365 ms     | 0      |
| 16          | 5.07 req/s | 422.7 tok/s          | 3190 ms     | 4541 ms     | 0      |

vLLM's continuous batching roughly doubles aggregate throughput from c8 to c16.

### Security — inline guardrails under adversarial load

Mixed traffic (clean + injection/jailbreak/PII), guardrails active:

- **100% of known-pattern attacks blocked** (38/38) with **0 false positives**
- Every block emits a structured security event (type, severity, stage) →
  Prometheus counters → SOC dashboard

### Security — benchmarked against NVIDIA Garak (the credibility centerpiece)

Instead of grading its own homework, the platform is tested with
[**NVIDIA Garak**](https://github.com/NVIDIA/garak), an open-source LLM
vulnerability scanner. `promptinject.AttackRogueString`, 256 adversarial prompts,
run against both the raw model and the guarded platform:

| Target | Attack success rate |
|--------|---------------------|
| Raw vLLM (no guardrails) | 48.4% |
| Guarded platform (guardrails inline) | 41.4% |

**The guardrails reduced successful injections by ~15% (relative) against Garak's
diverse probe set.** This is an honest defense-in-depth result — the pattern-based
detector catches known attack shapes but not every novel phrasing, exactly as its
[design notes](https://github.com/Arjun7114/llm-guardrails-gateway) state. A
measured, benchmarked number beats an unverifiable "100%."

---

## Architecture

```
User ─► Streamlit UI ─► FastAPI app layer ──────────────► vLLM (GPU) ─► tokens
                            │  pipeline (in order):          ▲
                            │   validate → auth →            │ OpenAI-compatible
                            │   INPUT GUARDRAILS →  ─────────┘  API on :8000
                            │   model call →
                            │   OUTPUT GUARDRAILS →
                            │   structured logging + metrics
                            │
                            ├─► security events ─► Prometheus ─► Grafana (SOC + perf dashboards)
                            └─► guardrails: llm-guardrails-gateway (injection / PII / policy)
```

Every layer is swappable via config: the model backend (mock for free local dev,
real vLLM in production) and the guardrails (passthrough by default, or the real
gateway) both plug in without touching endpoint code.

## Tech stack

| Layer | Tool |
|-------|------|
| Model serving | vLLM (OpenAI-compatible, PagedAttention, continuous batching) |
| Application layer | FastAPI (async, SSE streaming, API-key auth, Pydantic validation) |
| Security | Inline input/output guardrails + structured security telemetry |
| Red-team benchmark | NVIDIA Garak |
| UI | Streamlit (thin chat client) |
| Packaging | Docker + Docker Compose (readiness-gated startup) |
| Observability | Prometheus + Grafana (performance + security dashboards) |
| Cloud | AWS EC2 g5.xlarge (NVIDIA A10G) |

## What makes it distinct

1. **Inline, runtime defense of a live serving path** — a guardrail at the door of
   a running model, not offline log analysis.
2. **Security as a monitored control** — guardrail hits become typed, severity-rated
   telemetry on live dashboards.
3. **Performance measured under adversarial load**, and defense benchmarked against
   an industry-standard red-team tool.

See [POSITIONING.md](./POSITIONING.md) for how this relates to (without overlapping)
my other projects.

## Deployment

The full stack comes up with one command on a GPU host:

```bash
export HF_TOKEN=...        # Hugging Face read token
export API_KEY=...         # app-layer key
docker compose up
```

The **app waits for the model to finish loading** before accepting traffic
(`depends_on: service_healthy` gated on vLLM's `/health`). Full runbook in
[DEPLOY.md](./DEPLOY.md). Validated on AWS EC2 (see Results above).

## Repo map

```
app/         FastAPI app layer — pipeline, swappable backends, guardrails seam, telemetry
serving/     vLLM serving notes (flags, KV cache, troubleshooting)
ui/          thin Streamlit chat client
monitoring/  Prometheus config + Grafana dashboards (performance + SOC)
loadtest/    async load test (clean / attack / mixed modes)
garak/       NVIDIA Garak A/B benchmark configs + runbook
docker-compose.yml   orchestrated stack with readiness gate
DEPLOY.md    deployment runbook   ·   METRICS.md  full measured numbers
```

## Related projects

- [llm-guardrails-gateway](https://github.com/Arjun7114/llm-guardrails-gateway) —
  the reusable security control this platform runs every request through.
