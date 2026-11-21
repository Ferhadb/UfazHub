"""Measure public search and article feed latency against a local seeded API.

Run with the playground database and rate limiting disabled, for example:

    cd backend
    set -a; . .env.playground; set +a
    RATE_LIMIT_ENABLED=false uv run uvicorn app.main:app --port 8001
    uv run python ../scripts/loadtest.py --base-url http://127.0.0.1:8001 \
        --dataset-items 18

The numbers include HTTP, application, and database time on the local machine.
They are fixture-scale measurements, not production capacity estimates.
"""

import argparse
import asyncio
import math
import statistics
import time
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

ENDPOINTS = {
    "search": ("/api/search", {"q": "algorithm", "limit": "10"}),
    "feed": ("/api/feeds/articles.rss", {}),
}


@dataclass(frozen=True)
class Result:
    name: str
    requests: int
    concurrency: int
    elapsed_s: float
    latencies_ms: list[float]

    @property
    def requests_per_second(self) -> float:
        return self.requests / self.elapsed_s


def percentile(values: list[float], fraction: float) -> float:
    """Linear interpolation between adjacent ordered observations."""
    if not values:
        raise ValueError("cannot calculate a percentile of no samples")
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


async def request_once(
    client: httpx.AsyncClient, name: str, path: str, params: dict[str, str]
) -> float:
    start = time.perf_counter()
    response = await client.get(path, params=params)
    latency_ms = (time.perf_counter() - start) * 1000
    if response.status_code != 200:
        raise RuntimeError(
            f"{name}: HTTP {response.status_code}: {response.text[:200]}"
        )
    if name == "search" and "items" not in response.json():
        raise RuntimeError("search response has no items field")
    if name == "feed" and b"<rss" not in response.content:
        raise RuntimeError("feed response is not RSS")
    return latency_ms


async def measure(
    client: httpx.AsyncClient,
    name: str,
    requests: int,
    concurrency: int,
    warmup: int,
) -> Result:
    path, params = ENDPOINTS[name]
    for _ in range(warmup):
        await request_once(client, name, path, params)

    queue: asyncio.Queue[int] = asyncio.Queue()
    for index in range(requests):
        queue.put_nowait(index)
    samples: list[float] = []

    async def worker() -> None:
        while not queue.empty():
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            try:
                samples.append(await request_once(client, name, path, params))
            finally:
                queue.task_done()

    start = time.perf_counter()
    workers = [asyncio.create_task(worker()) for _ in range(min(requests, concurrency))]
    try:
        await asyncio.gather(*workers)
    except BaseException:
        for task in workers:
            task.cancel()
        await asyncio.gather(*workers, return_exceptions=True)
        raise
    elapsed = time.perf_counter() - start
    return Result(name, requests, concurrency, elapsed, samples)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--requests", type=int, default=400, help="per endpoint")
    parser.add_argument("--concurrency", type=int, default=20)
    parser.add_argument("--warmup", type=int, default=10, help="per endpoint")
    parser.add_argument(
        "--dataset-items",
        type=int,
        help="observed content_items count, recorded for result context",
    )
    args = parser.parse_args()
    parsed = urlparse(args.base_url)
    if parsed.scheme != "http" or parsed.hostname not in {
        "127.0.0.1",
        "localhost",
        "::1",
    }:
        parser.error("--base-url must be a local HTTP address")
    if min(args.requests, args.concurrency) < 1 or args.warmup < 0:
        parser.error(
            "requests and concurrency must be positive; warmup cannot be negative"
        )
    if args.dataset_items is not None and args.dataset_items < 0:
        parser.error("dataset-items cannot be negative")
    return args


async def main() -> None:
    args = parse_args()
    timeout = httpx.Timeout(30.0)
    limits = httpx.Limits(
        max_connections=args.concurrency, max_keepalive_connections=args.concurrency
    )
    async with httpx.AsyncClient(
        base_url=args.base_url, timeout=timeout, limits=limits
    ) as client:
        health = await client.get("/api/health")
        health.raise_for_status()
        print(
            f"target={args.base_url} requests_per_endpoint={args.requests} "
            f"concurrency={args.concurrency} warmup_per_endpoint={args.warmup} "
            f"dataset_items={args.dataset_items if args.dataset_items is not None else 'unknown'}"
        )
        for name in ENDPOINTS:
            result = await measure(
                client, name, args.requests, args.concurrency, args.warmup
            )
            print(
                f"{name}: completed={len(result.latencies_ms)} "
                f"elapsed={result.elapsed_s:.3f} s "
                f"throughput={result.requests_per_second:.1f} req/s "
                f"p50={statistics.median(result.latencies_ms):.1f} ms "
                f"p95={percentile(result.latencies_ms, 0.95):.1f} ms "
                f"max={max(result.latencies_ms):.1f} ms"
            )


if __name__ == "__main__":
    asyncio.run(main())
