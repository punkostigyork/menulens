from tempfile import SpooledTemporaryFile
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Scope, Receive, Send


class UploadLimitMiddleware:
    """Bound multipart bodies before parsing, including requests without Content-Length.

    Buffer at most 1 MiB in memory; close temporary storage on every exit.
    The service separately enforces the exact per-file limit.
    """
    def __init__(self, app: ASGIApp, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http" or scope["method"] != "POST" or scope["path"].rstrip("/") != "/api/menus":
            await self.app(scope, receive, send)
            return
        error = JSONResponse({"detail": "This upload is too large. Choose a smaller file."}, status_code=413)
        headers = dict(scope["headers"])
        try:
            declared = int(headers.get(b"content-length", b"0"))
        except ValueError:
            await JSONResponse({"detail": "Invalid request size."}, status_code=400)(scope, receive, send)
            return
        if declared > self.max_bytes:
            await error(scope, receive, send)
            return
        with SpooledTemporaryFile(max_size=1024 * 1024) as body:
            total = 0
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                chunk = message.get("body", b"")
                total += len(chunk)
                if total > self.max_bytes:
                    await error(scope, receive, send)
                    return
                body.write(chunk)
                if not message.get("more_body", False):
                    break
            body.seek(0)

            async def replay():
                chunk = body.read(64 * 1024)
                return {"type": "http.request", "body": chunk, "more_body": body.tell() < total}

            await self.app(scope, replay, send)
