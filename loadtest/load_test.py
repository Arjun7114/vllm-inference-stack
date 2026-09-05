"""
Load test for the inference stack.

Fires a fixed number of concurrent workers at the chat endpoint for a set
duration, then reports throughput and latency percentiles -- the headline
numbers for the README.

Self-contained: uses only httpx + asyncio (already in requirements). No external
load-testing tool needed, and every line is readable/explainable.

Usage:
    python load_test.py --url http://localhost:8080/v1/chat/completions \\
        --api-key dev-key-change-me --concurrency 16 --duration 60

Point --url at the app layer (recommended: measures the whole stack) or directly
at vLLM's /v1/chat/completions to measure the model server alone.
"""

import argparse
import asyncio
import time

import httpx

PROMPT = "Explain what an LLM inference server does, in about three sentences."


async def worker(client, url, headers, body, stop_at, results):
    """Loop sending requests until the deadline; record per-request stats."""
    while time.perf_counter() < stop_at:
        t0 = time.perf_counter()
        try:
            r = await client.post(url, headers=headers, json=body)
            elapsed = time.perf_counter() - t0
            if r.status_code == 200:
                data = r.json()
                completion_tokens = data.get("usage", {}).get("completion_tokens", 0)
                results.append((elapsed, completion_tokens, True))
            else:
                results.append((elapsed, 0, False))
        except Exception:
            results.append((time.perf_counter() - t0, 0, False))


def percentile(sorted_vals, p):
    if not sorted_vals:
        return 0.0
    k = max(0, min(len(sorted_vals) - 1, int(round((p / 100) * (len(sorted_vals) - 1)))))
    return sorted_vals[k]


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--api-key", default="dev-key-change-me")
    ap.add_argument("--model", default="mistralai/Mistral-7B-Instruct-v0.3")
    ap.add_argument("--concurrency", type=int, default=16)
    ap.add_argument("--duration", type=int, default=60, help="seconds")
    ap.add_argument("--max-tokens", type=int, default=128)
    args = ap.parse_args()

    headers = {"Authorization": f"Bearer {args.api_key}"}
    body = {
        "model": args.model,
        "messages": [{"role": "user", "content": PROMPT}],
        "max_tokens": args.max_tokens,
        "stream": False,
    }

    results: list[tuple[float, int, bool]] = []
    print(f"Load test: {args.concurrency} workers x {args.duration}s -> {args.url}")

    limits = httpx.Limits(max_connections=args.concurrency * 2)
    async with httpx.AsyncClient(timeout=120, limits=limits) as client:
        stop_at = time.perf_counter() + args.duration
        start = time.perf_counter()
        workers = [
            asyncio.create_task(worker(client, args.url, headers, body, stop_at, results))
            for _ in range(args.concurrency)
        ]
        await asyncio.gather(*workers)
        wall = time.perf_counter() - start

    # ---- compute stats ----
    latencies = sorted(e for e, _, ok in results if ok)
    ok = [r for r in results if r[2]]
    n_ok = len(ok)
    n_fail = len(results) - n_ok
    total_completion_tokens = sum(t for _, t, good in results if good)

    print("\n===== RESULTS =====")
    print(f"Duration (wall):      {wall:.1f}s")
    print(f"Requests OK:          {n_ok}")
    print(f"Requests failed:      {n_fail}")
    print(f"Error rate:           {(n_fail / max(1, len(results)) * 100):.2f}%")
    print(f"Throughput:           {n_ok / wall:.2f} req/s")
    print(f"Aggregate tokens/sec: {total_completion_tokens / wall:.1f} tok/s")
    if latencies:
        print(f"Latency p50:          {percentile(latencies, 50) * 1000:.0f} ms")
        print(f"Latency p95:          {percentile(latencies, 95) * 1000:.0f} ms")
        print(f"Latency p99:          {percentile(latencies, 99) * 1000:.0f} ms")
        print(f"Latency max:          {latencies[-1] * 1000:.0f} ms")
    print("===================")


if __name__ == "__main__":
    asyncio.run(main())
