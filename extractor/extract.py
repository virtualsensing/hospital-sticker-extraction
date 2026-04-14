"""Core extraction logic — send sticker image to Claude Vision API and parse response."""

import base64
import json
import re
import sys
from pathlib import Path

import anthropic
from PIL import Image

from .prompt import EXTRACTION_PROMPT
from .fields import FIELDS, validate_record

# Supported image formats and their MIME types
MIME_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".heic": "image/jpeg",  # converted to JPEG before sending
}

MAX_IMAGE_DIMENSION = 2048  # Claude vision max recommended size


def _convert_heic_to_jpeg(path: Path) -> bytes:
    """Convert HEIC to JPEG bytes using Pillow (requires pillow-heif)."""
    try:
        import pillow_heif
        pillow_heif.register_heif_opener()
    except ImportError:
        pass

    img = Image.open(path)
    from io import BytesIO
    buf = BytesIO()
    img = img.convert("RGB")
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def _prepare_image(path: Path) -> tuple[str, str]:
    """Read and prepare an image for the API. Returns (base64_data, media_type)."""
    suffix = path.suffix.lower()

    if suffix not in MIME_TYPES:
        raise ValueError(
            f"Unsupported image format: {suffix}. "
            f"Supported: {', '.join(MIME_TYPES.keys())}"
        )

    if suffix == ".heic":
        image_bytes = _convert_heic_to_jpeg(path)
        media_type = "image/jpeg"
    else:
        image_bytes = path.read_bytes()
        media_type = MIME_TYPES[suffix]

    # Resize if too large
    img = Image.open(path)
    w, h = img.size
    if max(w, h) > MAX_IMAGE_DIMENSION:
        ratio = MAX_IMAGE_DIMENSION / max(w, h)
        new_size = (int(w * ratio), int(h * ratio))
        img = img.resize(new_size, Image.LANCZOS)
        from io import BytesIO
        buf = BytesIO()
        fmt = "JPEG" if media_type == "image/jpeg" else "PNG"
        if img.mode == "RGBA" and fmt == "JPEG":
            img = img.convert("RGB")
        img.save(buf, format=fmt, quality=85)
        image_bytes = buf.getvalue()

    b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
    return b64, media_type


def _parse_json_response(text: str) -> dict:
    """Extract JSON from the API response text."""
    # Try direct parse first
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to extract JSON from markdown code fences
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try to find any JSON object in the text
    match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse JSON from API response:\n{text[:500]}")


def extract_from_image(
    image_path: str | Path,
    api_key: str | None = None,
    model: str = "claude-sonnet-4-20250514",
) -> dict:
    """Extract patient data from a single sticker image.

    Args:
        image_path: Path to the sticker photo.
        api_key: Anthropic API key. If None, reads from ANTHROPIC_API_KEY env var.
        model: Claude model to use (default: claude-sonnet-4-20250514).

    Returns:
        Dict with 16 extracted fields plus a 'warnings' list.
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")

    b64_data, media_type = _prepare_image(path)

    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": b64_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": EXTRACTION_PROMPT,
                    },
                ],
            }
        ],
    )

    response_text = message.content[0].text
    record = _parse_json_response(response_text)

    # Ensure all expected fields exist
    for field in FIELDS:
        if field not in record:
            record[field] = None

    # Validate and attach warnings
    record["_warnings"] = validate_record(record)
    record["_source_file"] = path.name

    return record


def extract_batch(
    image_paths: list[str | Path],
    api_key: str | None = None,
    model: str = "claude-sonnet-4-20250514",
    on_progress: callable = None,
) -> list[dict]:
    """Extract patient data from multiple sticker images.

    Args:
        image_paths: List of paths to sticker photos.
        api_key: Anthropic API key.
        model: Claude model to use.
        on_progress: Optional callback(index, total, filename) for progress reporting.

    Returns:
        List of extracted records.
    """
    results = []
    total = len(image_paths)

    for i, path in enumerate(image_paths):
        path = Path(path)
        if on_progress:
            on_progress(i + 1, total, path.name)

        try:
            record = extract_from_image(path, api_key=api_key, model=model)
            record["_status"] = "success"
        except Exception as e:
            record = {field: None for field in FIELDS}
            record["_status"] = "error"
            record["_error"] = str(e)
            record["_source_file"] = path.name
            record["_warnings"] = [f"Extraction failed: {e}"]
            print(f"  Error processing {path.name}: {e}", file=sys.stderr)

        results.append(record)

    return results
