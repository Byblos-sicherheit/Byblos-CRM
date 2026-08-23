from __future__ import annotations

import logging

from .app import create_app
from .config import load_settings
from .provider import AntigravityTextStreamer

settings = load_settings()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
app = create_app(settings, AntigravityTextStreamer(settings))
