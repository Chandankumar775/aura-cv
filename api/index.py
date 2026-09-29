"""Vercel serverless entry point: exposes the AURA-CV FastAPI app as `app` (ASGI).

Vercel serves the built UI (ui/dist) from its CDN and routes /api/* here. The hosted
build is a public demonstration: storage lives in /tmp and resets when an instance
recycles, and the UI labels it "Hosted demo, not air-gapped".

If start-up fails, the function still answers - with the error - so the cause shows in
the browser and in the function logs rather than as a bare FUNCTION_INVOCATION_FAILED.
"""

import json
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from aura.api.app import create_app

    app = create_app()
except Exception:  # pragma: no cover - only reached on a broken deployment
    _trace = traceback.format_exc()
    print(_trace, file=sys.stderr, flush=True)

    async def app(scope, receive, send):  # minimal ASGI app reporting the failure
        if scope["type"] != "http":
            return
        body = json.dumps({"error": {"code": "STARTUP_FAILED", "message": "AURA-CV could not start on this host.",
                                     "details": {"traceback": _trace.splitlines()[-12:]}}}).encode()
        await send({"type": "http.response.start", "status": 500, "headers": [(b"content-type", b"application/json")]})
        await send({"type": "http.response.body", "body": body})
