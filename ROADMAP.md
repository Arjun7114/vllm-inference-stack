# Roadmap

This project is built in phases. Each phase ends in something that runs and is
committed on its own feature branch, then merged into `main` via a pull request.

| Phase | Focus | New skill | Status |
|-------|-------|-----------|--------|
| 0 | Foundations & repo setup | Framing a project so its intent is obvious | ✅ |
| 1 | Serve the model with vLLM | vLLM flags, KV cache, PagedAttention, token-as-secret | ⬜ |
| 2 | App layer skeleton (modular pipeline) | Middleware pattern, FastAPI DI, Pydantic validation | ⬜ |
| 3 | Token streaming (SSE) | Server-sent events, async generators | ⬜ |
| 4 | Streamlit chat UI (thin) | Streaming render in Streamlit | ⬜ |
| 5 | Guardrails plug-in | Clean plug-in interface, security at the boundary | ⬜ |
| 6 | Dockerize + readiness gating | GPU containers, compose orchestration, startup ordering | ⬜ |
| 7 | Observability | Inference-layer metrics (Prometheus + Grafana) | ⬜ |
| 8 | Load test & real numbers | Load testing, reading throughput | ⬜ |
| 9 | AWS deployment | Cloud GPU provisioning, repeatable deploy runbook | ⬜ |
| 10 | Polish (optional) | Quantization experiment, diagram, demo GIF | ⬜ |

## Design principles

- **The serving layer is the star.** This is an inference-infrastructure project,
  not a chat app. The UI is deliberately thin.
- **Portable by default.** Everything is containerized so it runs unchanged on a
  rented GPU, a local GPU, or an AWS GPU instance.
- **Security at the boundary is pluggable.** Guardrails are an optional step in
  the request pipeline; the default is a no-op passthrough so the repo runs for
  anyone who clones it.

## Model

- **Primary:** `mistralai/Mistral-7B-Instruct-v0.3` (gated — used deliberately to
  practice the Hugging Face token-as-secret flow).
- **Fallback:** `Qwen/Qwen2.5-7B-Instruct` (ungated — use if access approval is
  delayed, so the build is never blocked).

Both fit a 24 GB GPU in FP16 with room for the KV cache.
