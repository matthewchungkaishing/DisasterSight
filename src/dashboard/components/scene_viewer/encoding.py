"""Encode PIL images for inline dashboard viewing."""

from __future__ import annotations

import base64
from io import BytesIO

from PIL import Image


def image_to_data_uri(image: Image.Image) -> str:
    """Encode a display image losslessly for the dashboard viewer."""
    buffer = BytesIO()
    image.convert("RGB").save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"
