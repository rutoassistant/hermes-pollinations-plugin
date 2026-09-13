"""Pollinations image generation provider.

Supports both authenticated (gen.pollinations.ai) and legacy free (image.pollinations.ai) endpoints.
If POLLINATIONS_API_KEY is set, uses authenticated API; falls back to legacy free endpoint.
"""

from __future__ import annotations

import base64
import logging
import os
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent.image_gen_provider import (
    DEFAULT_ASPECT_RATIO,
    ImageGenProvider,
    error_response,
    save_b64_image,
    save_url_image,
    success_response,
)

logger = logging.getLogger(__name__)

_MODELS = {
    "flux": {"display": "Flux", "speed": "~5-10s", "strengths": "High quality"},
    "klein": {"display": "Klein", "speed": "~2-5s", "strengths": "Fast"},
    "zimage": {"display": "Z-Image", "speed": "~3-8s", "strengths": "Artistic"},
}
_DEFAULT_MODEL = "flux"


class PollinationsImageGenProvider(ImageGenProvider):
    """Pollinations.ai image generation with API key and legacy fallback."""

    @property
    def name(self) -> str:
        return "pollinations"

    @property
    def display_name(self) -> str:
        return "Pollinations"

    def is_available(self) -> bool:
        return True  # Always available (either with API key or legacy fallback)

    def list_models(self) -> List[Dict[str, Any]]:
        return [
            {"id": model_id, "display": meta["display"], "speed": meta["speed"], "strengths": meta["strengths"]}
            for model_id, meta in _MODELS.items()
        ]

    def default_model(self) -> Optional[str]:
        return _DEFAULT_MODEL

    def capabilities(self) -> Dict[str, Any]:
        return {"modalities": ["text"], "max_reference_images": 0}

    def _get_api_key(self) -> Optional[str]:
        """Check for Pollinations API key in environment or Hermes .env file."""
        # Check environment first
        key = os.environ.get("POLLINATIONS_API_KEY")
        if key:
            return key

        # Try to load from Hermes .env file
        try:
            home = os.getenv("HERMES_HOME", Path.home() / ".hermes")
            env_path = Path(home) / ".env"
            if env_path.is_file():
                for line in env_path.read_text().splitlines():
                    stripped = line.strip()
                    if stripped.startswith("POLLINATIONS_API_KEY="):
                        value = stripped.split("=", 1)[1].strip().strip('"').strip("'")
                        if value:
                            return value
        except Exception:
            pass

        return None

    def generate(
        self,
        prompt: str,
        aspect_ratio: str = DEFAULT_ASPECT_RATIO,
        *,
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        prompt = (prompt or "").strip()
        if not prompt:
            return error_response(error="Prompt is required", error_type="invalid_argument", provider="pollinations")

        model_id = model if model in _MODELS else _DEFAULT_MODEL

        size_map = {
            "square": ("1024", "1024"),
            "landscape": ("1280", "768"),
            "portrait": ("768", "1280"),
        }
        width, height = size_map.get(aspect_ratio, ("1024", "1024"))
        seed = kwargs.get("seed", 42)

        api_key = self._get_api_key()

        # Try authenticated API first if key is available
        if api_key:
            try:
                logger.info("Using authenticated Pollinations API (gen.pollinations.ai)")
                url = f"https://gen.pollinations.ai/image/{urllib.parse.quote(prompt)}?model={model_id}&width={width}&height={height}&seed={seed}&key={api_key}"
                saved = save_url_image(url, prefix=f"pollinations_{model_id}")
                return success_response(
                    image=str(saved),
                    model=model_id,
                    prompt=prompt,
                    aspect_ratio=aspect_ratio,
                    provider="pollinations",
                    extra={"auth": "api_key"},
                )
            except Exception as exc:
                logger.warning("Authenticated Pollinations API failed: %s. Falling back to legacy free endpoint.", exc)

        # Fallback to legacy free endpoint
        try:
            logger.info("Using legacy free Pollinations API (image.pollinations.ai)")
            url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?model={model_id}&width={width}&height={height}&seed={seed}"

            req = urllib.request.Request(url, headers={"User-Agent": "Hermes/1.0"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = resp.read()

            b64 = base64.b64encode(data).decode("utf-8")
            saved = save_b64_image(b64, prefix=f"pollinations_{model_id}")
            return success_response(
                image=str(saved),
                model=model_id,
                prompt=prompt,
                aspect_ratio=aspect_ratio,
                provider="pollinations",
                extra={"auth": "legacy_free"},
            )

        except Exception as exc:
            logger.warning("Legacy Pollinations generation failed: %s", exc)
            return error_response(
                error=f"Pollinations failed (authenticated and legacy both failed): {exc}",
                error_type="api_error",
                provider="pollinations",
            )

    def get_setup_schema(self) -> Dict[str, Any]:
        return {
            "name": "Pollinations",
            "badge": "freemium",
            "tag": "Pollinations AI (API key or free legacy fallback)",
            "env_vars": [
                {
                    "key": "POLLINATIONS_API_KEY",
                    "prompt": "Pollinations API key (optional - leave blank for free tier)",
                    "url": "https://enter.pollinations.ai",
                }
            ],
        }


def register(ctx) -> None:
    ctx.register_image_gen_provider(PollinationsImageGenProvider())
