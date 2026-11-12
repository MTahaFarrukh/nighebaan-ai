"""Body-size enforcement before multipart parsing can spool uploads."""

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.services.media_config import MAX_BYTES


class UploadLimitMiddleware:
    """Bound the complete multipart body, including chunked uploads, in memory."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not scope["path"].endswith("/analyze/file"):
            return await self.app(scope, receive, send)
        cap = (
            MAX_BYTES + 1024 * 1024
        )  # bounded multipart overhead; file itself has a stricter limit
        headers = dict(scope.get("headers", []))
        length = headers.get(b"content-length")
        if length and (not length.isdigit() or int(length) > cap):
            return await JSONResponse(
                {"detail": "Upload request exceeds the size limit."}, status_code=413
            )(scope, receive, send)
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > cap:
                return await JSONResponse(
                    {"detail": "Upload request exceeds the size limit."},
                    status_code=413,
                )(scope, receive, send)
            if not message.get("more_body", False):
                break
        consumed = False

        async def replay() -> Message:
            nonlocal consumed
            if not consumed:
                consumed = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, replay, send)
