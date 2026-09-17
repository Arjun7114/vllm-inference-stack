# Garak A/B Benchmark — Results

Benchmarking the platform's inline guardrails against
[NVIDIA Garak](https://github.com/NVIDIA/garak) v0.16.1, an open-source LLM
vulnerability scanner ("nmap for LLMs"). Rather than testing the guardrails
against hand-picked attack strings, we measure them against Garak's standardized
adversarial probes — and compare the guarded platform to the raw, unprotected
model.

## Method

Both runs targeted the same Mistral-7B deployment on AWS EC2 (g5.xlarge, A10G),
via Garak's `OpenAICompatible` generator, using the probe
`promptinject.AttackRogueString` (256 adversarial prompts, `-g 1`).

- **Run A — raw vLLM** (`http://<host>:8000/v1/`, no guardrails): the model's
  native resistance with zero protection.
- **Run B — guarded platform** (`http://<host>:8081/v1/`, guardrails inline):
  attacks pass through the app layer, where the guardrails block injections
  (HTTP 400) before they reach the model. Garak scores a blocked/refused attack
  as a PASS.

Config files: `garak-raw-vllm.yaml` and `garak-through-guardrails.yaml`
(the AWS runs used `garak-aws-raw.yaml` / `garak-aws-guarded.yaml` with the
instance's public IP).

## Results

| Target | Prompts | Attacks refused | Attack success rate |
|--------|---------|-----------------|---------------------|
| Run A — raw vLLM (no guardrails) | 256 | 132 | **48.4%** |
| Run B — guarded platform | 256 | 150 | **41.4%** |

**The guardrails reduced the attack success rate from 48.4% to 41.4% — a ~7
percentage-point absolute, ~15% relative reduction in successful injections.**

Each run took ~8 minutes (hundreds of real generations against the model).
During Run B, the app layer logged a stream of structured `security event`
records as the guardrails blocked Garak's attacks in real time.

## Analysis (the honest part)

This is a **defense-in-depth** result, not a claim of perfect security — and that
distinction is the point.

- **The guardrails are pattern-based.** They catch known injection shapes
  ("ignore previous instructions", "DAN", etc.) reliably, but Garak's
  `AttackRogueString` deliberately uses many diverse and novel phrasings, some of
  which slip past a denylist. This is exactly the limitation documented in the
  [gateway's design notes](https://github.com/Arjun7114/llm-guardrails-gateway):
  a denylist raises the attacker's cost but is not a complete solution.
- **The model has some native resistance.** Even raw vLLM refused ~52% of the
  attacks on its own — instruction-tuned models resist obvious injections. The
  guardrails add a layer on top, pushing refusal from ~52% to ~59%.
- **Why report this instead of the 100% from the load test?** The internal load
  test uses known-pattern attacks the denylist is built for, so it blocks 100% —
  true, but it grades its own homework. Garak is an independent, industry-standard
  red-team tool with a far harder and more varied probe set. A measured
  improvement against Garak is a more credible, honest security claim than a
  perfect score against self-selected inputs.

## How to strengthen the defense (next steps)

- Add a **trained injection classifier** (e.g. a small fine-tuned model)
  alongside the denylist to catch novel phrasings the patterns miss.
- Expand probe coverage (encoding attacks, multilingual, `dan` family) and track
  the block rate per probe over time.
- Feed Garak results back into the guardrail rules — closing the loop between
  red-team findings and defense improvements.

## Reproduce

See [README.md](./README.md) in this folder for the exact install and run
commands.
