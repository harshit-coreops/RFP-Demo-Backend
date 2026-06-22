import time

from . import metrics


class MetricsMiddleware:
    """Times every API request and feeds the metrics collector."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.perf_counter()
        response = self.get_response(request)
        if request.path.startswith("/api/"):
            metrics.record(request.path, request.method, time.perf_counter() - start)
        return response
