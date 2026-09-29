"""Vercel entry point (FastAPI preset): the top-level `app` below is the ASGI app.

FastAPI serves everything: /api/* and the built UI in ui/dist (committed so it is always
in the function bundle). The hosted build is a public demonstration: storage lives in
/tmp and resets when an instance recycles, and the UI labels it "Hosted demo, not air-gapped".
If start-up fails, the function answers with the error instead of a bare 500.
"""

import json
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _build():
    try:
        from aura.api.app import create_app

        return create_app()
    except Exception:  # only reached on a broken deployment
        trace = traceback.format_exc()
        print(trace, file=sys.stderr, flush=True)

        async def failed(scope, receive, send):
            if scope["type"] != "http":
                return
            body = json.dumps({"error": {"code": "STARTUP_FAILED", "message": "AURA-CV could not start on this host.",
                                         "details": {"traceback": trace.splitlines()[-12:]}}}).encode()
            await send({"type": "http.response.start", "status": 500, "headers": [(b"content-type", b"application/json")]})
            await send({"type": "http.response.body", "body": body})

        return failed


app = _build()
