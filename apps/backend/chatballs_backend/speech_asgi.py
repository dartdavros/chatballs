"""Django ASGI normally spools the body before upload handlers run.

The dictation path must not write to disk, including the ASGI request spool.
Keep its body in bounded memory; other application paths retain Django behavior.
"""

from io import BytesIO

from django.core.asgi import get_asgi_application
from django.core.exceptions import RequestAborted
from django.core.handlers.asgi import ASGIHandler

MAX_DICTATION_BODY = 10 * 1024 * 1024 + 65536


class DictationASGIHandler(ASGIHandler):
    async def read_body(self, receive):
        body = BytesIO()
        try:
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    raise RequestAborted()
                chunk = message.get("body", b"")
                if body.tell() + len(chunk) > MAX_DICTATION_BODY:
                    raise RequestAborted()
                body.write(chunk)
                if not message.get("more_body", False):
                    break
            body.seek(0)
            return body
        except BaseException:
            body.close()
            raise


def speech_safe_application():
    application = get_asgi_application()
    dictation = DictationASGIHandler()

    async def dispatch(scope, receive, send):
        if scope.get("path") != "/api/v1/webchat/dictation/":
            return await application(scope, receive, send)
        for header, value in scope.get("headers", []):
            if header.lower() == b"content-length":
                try:
                    oversized = int(value) > MAX_DICTATION_BODY
                except ValueError:
                    oversized = True
                if oversized:
                    await send({"type": "http.response.start", "status": 413, "headers": []})
                    return await send({"type": "http.response.body", "body": b""})
        return await dictation(scope, receive, send)

    return dispatch
