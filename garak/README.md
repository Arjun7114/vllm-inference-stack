# Garak Security Benchmark

Benchmarks this platform's guardrails against **NVIDIA Garak**, an open-source LLM
vulnerability scanner (the "nmap for LLMs"). Instead of hand-picked attack
strings, we measure the guardrails against Garak's standardized adversarial probes.

## The experiment: A/B comparison

We run Garak twice and compare the results. The difference is the guardrails'
measured value.

- **Run A — raw vLLM (no guardrails):** Garak attacks the model directly on
  port 8000. Measures the model's *native* vulnerability.
- **Run B — through the app layer (guardrails ON):** Garak attacks via port 8080.
  The guardrails block attacks (HTTP 400) before they reach the model. Garak
  scores a blocked/refused attack as a PASS, so **Garak's pass rate = the
  guardrail block rate**.

The drop in successful attacks from A to B is the headline result:
> "Against Garak's promptinject + dan probes, the unprotected model failed N
>  attacks; with guardrails inline, failures dropped to M."

## Scope (deliberate)

- Run **2-3 probe families**, not `--probes all` (a full sweep takes hours).
- Use **`--generations 1`** to keep each run fast.
- **Do NOT** run the `atkgen` family -- it uses an attacker LLM and costs money.

Chosen probes (aligned to what the guardrails defend):
- `promptinject` — prompt-injection attacks
- `dan` — jailbreak / "do anything now" attacks

## Commands

Install (Python 3.10-3.12):
```bash
python -m pip install -U garak
```

Run A — raw vLLM (guardrails OFF), vLLM running on :8000:
```bash
python -m garak --config garak/garak-raw-vllm.yaml \
  --probes promptinject,dan --generations 1
```

Run B — through guardrails, app layer running on :8080:
```bash
python -m garak --config garak/garak-through-guardrails.yaml \
  --probes promptinject,dan --generations 1
```

Garak writes a JSONL log and an HTML report per run. Record the per-probe pass
rates from each, and the A->B improvement, in METRICS.md.

## Reading results

A line like `promptinject.HijackHateHumans: PASS ok on 95/100` means 95 of 100
injection attempts were refused/blocked. Higher pass rate = stronger defense.
Compare the same probe's pass rate in Run A vs Run B to see the guardrails' effect.
