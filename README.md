# vLLM Inference Stack

Serve an open-source LLM on a GPU with **vLLM**, front it with a modular
**FastAPI** application layer, expose a thin **Streamlit** chat UI, and package
the whole thing with **Docker** so it runs unchanged on any compatible GPU
machine.

> This is a **model-serving / inference-infrastructure** project. The chat UI is
> deliberately thin — the interesting engineering is everything *underneath* it:
> loading weights onto the GPU, managing VRAM and the KV cache, batching and
> streaming requests, gating startup on model readiness, and observing it all
> like production infrastructure.

**Status:** 🚧 Built in phases — see [ROADMAP.md](./ROADMAP.md).

---

## Why this exists

Putting a model behind an API is easy to demo and hard to do *well*. Most
tutorials stop at "it streams tokens." This project goes after the operational
layer that real inference services need:

- **Serving** — vLLM with an OpenAI-compatible endpoint, with deliberate control
  over GPU memory, context length, dtype, and quantization.
- **An application layer** — auth, validation, structured logging, and a
  **pluggable guardrails step** for input/output safety, all as an ordered
  request pipeline.
- **Operations** — containerized with a readiness gate so traffic waits for the
  model to finish loading; observed with Prometheus + Grafana; benchmarked under
  load with real throughput and latency numbers.

## Architecture

```
                         (diagram added in a later phase)

  User ──► Streamlit UI ──► FastAPI app layer ──► vLLM (GPU) ──► tokens stream back
                                │
                                └─ pipeline: auth → validation → [guardrails] → model → output guardrails
```

## Tech stack

| Layer | Tool |
|-------|------|
| Model serving | vLLM (OpenAI-compatible server) |
| Application layer | FastAPI |
| Chat UI | Streamlit |
| Guardrails (pluggable) | llm-guardrails-gateway |
| Packaging | Docker + Docker Compose |
| Observability | Prometheus + Grafana |
| Load testing | k6 / Locust |
| Cloud | AWS GPU instance |

## Project structure

```
vllm-inference-stack/
├── serving/        # vLLM start script + serving notes
├── app/            # FastAPI application layer (the request pipeline)
├── ui/             # thin Streamlit chat interface
├── docker/         # Dockerfiles + docker-compose
├── monitoring/     # Prometheus config + Grafana dashboards
├── loadtest/       # load-test scripts + results
├── ROADMAP.md
├── LICENSE
└── README.md
```

## Getting started

Setup and run instructions are added phase by phase as each layer lands.
See [ROADMAP.md](./ROADMAP.md) for the current state.

## Related projects

- [llm-guardrails-gateway](https://github.com/Arjun7114/llm-guardrails-gateway) —
  the security boundary that plugs into this stack's request pipeline.
