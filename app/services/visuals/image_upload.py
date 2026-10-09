"""Bounded browser image reads and slot-specific Pillow validation."""

from __future__ import annotations

import asyncio
import warnings
from dataclasses import dataclass
from io import BytesIO

from fastapi import UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.exceptions import ValidationError

UPLOAD_CHUNK_BYTES = 1024 * 1024
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_IMAGE_PIXELS = 24_000_000
SUPPORTED_FORMATS = {"PNG", "JPEG", "WEBP"}


@dataclass(frozen=True)
class PreparedImage:
    """A validated, normalized PNG ready for atomic persistence."""

    content: bytes
    width: int
    height: int
    source_format: str
    has_alpha: bool

    def validation(self) -> dict:
        return {
            "width": self.width, "height": self.height, "source_format": self.source_format,
            "has_alpha": self.has_alpha, "normalized_format": "PNG",
        }


async def read_upload(file: UploadFile) -> tuple[str, bytes]:
    """Read one upload in bounded chunks and always close its temporary handle."""
    content = bytearray()
    try:
        while chunk := await file.read(UPLOAD_CHUNK_BYTES):
            content.extend(chunk)
            if len(content) > MAX_UPLOAD_BYTES:
                raise ValidationError("Character pictures must be 20 MB or smaller")
        if not content:
            raise ValidationError("Uploaded character picture is empty")
        return file.filename or "picture", bytes(content)
    finally:
        await file.close()


def _prepare_sync(content: bytes, contract: dict) -> PreparedImage:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(content)) as probe:
                source_format = probe.format or ""
                width, height = probe.size
                if width * height > MAX_IMAGE_PIXELS:
                    raise ValidationError("Image exceeds the 24 megapixel safety limit")
                probe.verify()
            if source_format not in SUPPORTED_FORMATS:
                raise ValidationError("Supported image formats are PNG, JPEG and WebP")
            with Image.open(BytesIO(content)) as opened:
                picture = ImageOps.exif_transpose(opened)
                picture.load()
                width, height = picture.size
                if contract.get("exact_size") and (width, height) != tuple(contract["exact_size"]):
                    expected = contract["exact_size"]
                    raise ValidationError(f"{contract['title']} must be exactly {expected[0]}x{expected[1]}")
                minimum = contract.get("minimum_size", (512, 512))
                if width < minimum[0] or height < minimum[1]:
                    raise ValidationError(f"{contract['title']} must be at least {minimum[0]}x{minimum[1]}")
                has_alpha = "A" in picture.getbands()
                if contract.get("transparent"):
                    if source_format != "PNG" or not has_alpha:
                        raise ValidationError("Sprite slots require a transparent PNG")
                    rgba = picture.convert("RGBA")
                    alpha = rgba.getchannel("A")
                    corners = (alpha.getpixel((0, 0)), alpha.getpixel((width - 1, 0)),
                               alpha.getpixel((0, height - 1)), alpha.getpixel((width - 1, height - 1)))
                    if any(value > 20 for value in corners):
                        raise ValidationError("Sprite background must be transparent at all four corners")
                    if alpha.getbbox() is None:
                        raise ValidationError("Sprite picture is empty")
                    edge_pixels = (
                        sum(alpha.getpixel((x, 0)) > 20 for x in range(width))
                        + sum(alpha.getpixel((0, y)) > 20 for y in range(height))
                        + sum(alpha.getpixel((width - 1, y)) > 20 for y in range(height))
                    )
                    if edge_pixels > 40:
                        raise ValidationError("Sprite figure is cut by the top, left, or right canvas edge")
                    normalized = rgba
                else:
                    normalized = picture.convert("RGBA" if has_alpha else "RGB")
                output = BytesIO()
                normalized.save(output, format="PNG", optimize=True)
    except ValidationError:
        raise
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ValidationError("Uploaded file is not a safe readable image") from exc
    return PreparedImage(output.getvalue(), width, height, source_format, has_alpha)


async def prepare_image(content: bytes, contract: dict) -> PreparedImage:
    """Verify and normalize image bytes outside the event loop."""
    return await asyncio.to_thread(_prepare_sync, content, contract)
