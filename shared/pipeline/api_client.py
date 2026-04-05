"""Gemini API client for image generation."""

import base64
import time
from pathlib import Path
from typing import Optional

from google import genai
from google.genai import types


class GeminiImageClient:
    """Wrapper around the Google GenAI SDK for image generation."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-3-pro-image-preview",
        image_size: str = "4K",
        aspect_ratio: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 5.0,
        rate_limit_rpm: int = 10,
    ):
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.image_size = image_size
        self.aspect_ratio = aspect_ratio  # e.g. "4:5", "9:16", "16:9"
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.min_interval = 60.0 / rate_limit_rpm
        self._last_call_time = 0.0

    def _rate_limit(self):
        """Sleep if needed to stay under the RPM limit."""
        elapsed = time.time() - self._last_call_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_call_time = time.time()

    def _load_image_bytes(self, path: Path) -> bytes:
        """Read an image file as bytes."""
        with open(path, "rb") as f:
            return f.read()

    def _get_mime_type(self, path: Path) -> str:
        """Determine MIME type from file extension."""
        suffix = path.suffix.lower()
        mime_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
        }
        return mime_map.get(suffix, "image/jpeg")

    def generate(
        self,
        product_image_path: Path,
        reference_image_path: Path,
        prompt: str,
        system_instruction: str = "",
    ) -> Optional[bytes]:
        """
        Generate a lifestyle image using product flatlay + reference image.

        Args:
            product_image_path: Path to the product flatlay photo
            reference_image_path: Path to the reference lifestyle photo
            prompt: The rendered prompt text
            system_instruction: Optional system instruction

        Returns:
            Image bytes (PNG) or None if generation failed
        """
        # Build content parts
        product_bytes = self._load_image_bytes(product_image_path)
        reference_bytes = self._load_image_bytes(reference_image_path)

        contents = [
            types.Part.from_bytes(
                data=product_bytes,
                mime_type=self._get_mime_type(product_image_path),
            ),
            types.Part.from_text(text="Above: The exact garment to reproduce (flatlay product photo)."),
            types.Part.from_bytes(
                data=reference_bytes,
                mime_type=self._get_mime_type(reference_image_path),
            ),
            types.Part.from_text(text="Above: The reference scene, pose, and lighting to match."),
            types.Part.from_text(text=prompt),
        ]

        # Config
        image_config = {}
        if self.aspect_ratio:
            image_config["aspect_ratio"] = self.aspect_ratio

        config = types.GenerateContentConfig(
            response_modalities=["IMAGE", "TEXT"],
            system_instruction=system_instruction if system_instruction else None,
        )

        # Call with retry
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                self._rate_limit()
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=config,
                )

                # Extract image from response
                if response.candidates:
                    for part in response.candidates[0].content.parts:
                        if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                            return part.inline_data.data

                print(f"  Warning: No image in response (attempt {attempt}/{self.max_retries})")
                last_error = "No image returned in response"

            except Exception as e:
                last_error = str(e)
                error_lower = str(e).lower()

                # Don't retry on auth errors
                if "api key" in error_lower or "401" in error_lower or "403" in error_lower:
                    print(f"  Error: Authentication failed: {e}")
                    raise

                # Retry on rate limit or server errors
                if "429" in error_lower or "500" in error_lower or "503" in error_lower:
                    wait = self.retry_delay * attempt
                    print(f"  Retrying in {wait}s (attempt {attempt}/{self.max_retries}): {e}")
                    time.sleep(wait)
                    continue

                # Unknown error
                print(f"  Error (attempt {attempt}/{self.max_retries}): {e}")
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)

        print(f"  Failed after {self.max_retries} attempts: {last_error}")
        return None
