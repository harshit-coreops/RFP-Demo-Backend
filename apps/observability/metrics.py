"""Lightweight in-process metrics for the Platform Health screen + /metrics.

Real observability without a heavyweight stack: a Prometheus registry (scrapable
at /api/metrics) plus rolling latency samples used to compute live P95. The
process start time gives true uptime. On a multi-process deployment these are
per-worker; the Prometheus endpoint is the cross-worker aggregation point."""
from __future__ import annotations

import time
from collections import deque
from threading import Lock

from prometheus_client import Counter, Histogram

# Monotonic-safe start timestamp (wall clock for human display).
_START = time.time()

# Rolling latency samples (seconds) for live P95 on the dashboard.
_AI_SAMPLES: deque[float] = deque(maxlen=500)
_HTTP_SAMPLES: deque[float] = deque(maxlen=1000)
_lock = Lock()

# Prometheus metrics (scraped at /api/metrics/).
REQUESTS = Counter("rfp_http_requests_total", "HTTP requests", ["path_group", "method"])
AI_LATENCY = Histogram("rfp_ai_inference_seconds", "AI inference latency (s)")
HTTP_LATENCY = Histogram("rfp_http_request_seconds", "HTTP request latency (s)")

_AI_PATHS = ("/generate/", "/suggestions/", "/classify/", "/recommendation/", "/compliance/")


def record(path: str, method: str, seconds: float) -> None:
    group = "ai" if any(p in path for p in _AI_PATHS) else "http"
    REQUESTS.labels(group, method).inc()
    HTTP_LATENCY.observe(seconds)
    with _lock:
        _HTTP_SAMPLES.append(seconds)
        if group == "ai":
            AI_LATENCY.observe(seconds)
            _AI_SAMPLES.append(seconds)


def _p95(samples) -> float:
    if not samples:
        return 0.0
    s = sorted(samples)
    return s[min(len(s) - 1, int(round(0.95 * (len(s) - 1))))]


def uptime_seconds() -> float:
    return time.time() - _START


def snapshot() -> dict:
    with _lock:
        ai = list(_AI_SAMPLES)
        http = list(_HTTP_SAMPLES)
    return {
        "uptime_seconds": round(uptime_seconds(), 1),
        "ai_p95_ms": round(_p95(ai) * 1000, 1),
        "http_p95_ms": round(_p95(http) * 1000, 1),
        "ai_requests": len(ai),
        "http_requests": len(http),
    }
