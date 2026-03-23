from .bootstrap import ensure_runtime_bootstrap


class EnsureSchemaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ensure_runtime_bootstrap()
        return self.get_response(request)
