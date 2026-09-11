# Positioning & Differentiation

What this project is, what makes it distinct, and how it relates to (without
overlapping) my other work. This is the one-paragraph answer to "why does this
exist and how is it different?"

## One-line identity

**An LLM inference platform that defends itself at runtime and proves it.**
A vLLM serving stack where every request passes inline through a security
boundary, and that defense is measured and monitored like production
infrastructure — throughput, latency, and *attacks blocked*, live.

## The three domains, made concrete

- **AI** — serves an open-source LLM (Mistral-7B) on GPU with vLLM: KV cache,
  PagedAttention, batching, token streaming, an OpenAI-compatible API.
- **Cloud / DevOps** — swappable backends, containerized, a readiness-gated
  Docker Compose stack, observability (Prometheus + Grafana), deployable to a
  cloud GPU host.
- **Security** — inline input/output guardrails (prompt injection, PII,
  jailbreak, policy) on every request, emitting structured security telemetry to
  a live monitoring dashboard.

## What makes it unique (the sharp edges)

1. **Inline, runtime defense of a *live serving path* — not offline analysis.**
   The security control sits *in the request path* of a running model and blocks
   attacks before they reach it. This is a guardrail at the door, not an analyst
   reviewing logs after the fact.

2. **Security as a *monitored control*, not just a check.** Guardrail hits become
   typed, severity-rated, structured security events feeding Prometheus + Grafana
   SOC-style dashboards: attacks over time, by type, block rate, recent-attacks
   feed. Most "I served an LLM" projects have no security layer at all; most
   "LLM security" projects aren't wired into a real serving platform with
   observability.

3. **Performance measured *under adversarial load*.** The load test mixes real
   attack payloads with clean traffic, so the headline numbers are not just
   "X req/s" but "X req/s while detecting and blocking Y% of injection attempts."

## How it relates to my other projects (complementary, not overlapping)

- **llm-guardrails-gateway** — the reusable *security control*. This project is a
  *consumer* of it: it wires the gateway into a serving stack and adds runtime
  observability. One builds the control; this one operates and monitors it.

- **Cortex-Chain** — an *offline SOC / threat-analysis pipeline* with tamper-
  evident audit. Deliberately different lane: this project is *inline, real-time
  serving-layer defense*, not after-the-fact investigation. To keep them
  distinct, this repo stays on the "runtime protection of a live inference
  platform" side and does not add offline analysis or audit-chain features.

## The vision it belongs to

This is the **LLM-security module of a broader cloud-security observability
system (CloudSentinel-AI)**: telemetry -> detection -> monitoring, scoped here to
LLM traffic. Built as a finished, focused module first; the broader system builds
on top of it.
