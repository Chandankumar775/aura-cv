"""Vercel serverless entry point: exposes the AURA-CV FastAPI app as `app` (ASGI).

Vercel serves the built UI (ui/dist) from its CDN and routes /api/* here. The hosted
build is a public demonstration: storage lives in /tmp and resets when an instance
recycles, and the UI labels it "Hosted demo, not air-gapped".
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aura.api.app import create_app  # noqa: E402

app = create_app()
