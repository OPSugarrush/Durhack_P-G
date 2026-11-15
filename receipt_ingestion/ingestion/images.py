"""Bounded in-memory image decoding and PDF rasterisation."""
import base64
import io
from pathlib import Path
from PIL import Image, ImageOps

MAX_BYTES = 20 * 1024 * 1024
MAX_PAGES = 5
MAX_PIXELS = 25_000_000


def _encode(image):
    if image.width * image.height > MAX_PIXELS:
        raise ValueError("Image exceeds 25 megapixels")
    image = ImageOps.exif_transpose(image).convert("RGB")
    image.thumbnail((2400, 3200))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode()


def prepare_images(data: bytes, filename: str) -> list[str]:
    if not data or len(data) > MAX_BYTES:
        raise ValueError("Upload must contain 1 byte to 20 MB")
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        import pypdfium2 as pdfium
        if not data.startswith(b"%PDF-"):
            raise ValueError("Invalid PDF signature")
        with pdfium.PdfDocument(data) as document:
            if not 1 <= len(document) <= MAX_PAGES:
                raise ValueError("PDF must contain 1 to 5 pages of one receipt")
            result = []
            for page in document:
                try:
                    width, height = page.get_size()
                    scale = min(2.5, 2400 / max(width, height))
                    bitmap = page.render(scale=scale)
                    try:
                        result.append(_encode(bitmap.to_pil()))
                    finally:
                        bitmap.close()
                finally:
                    page.close()
            return result
    if suffix not in {".jpg", ".jpeg", ".png"}:
        raise ValueError("Supported files: JPG, PNG, PDF")
    with Image.open(io.BytesIO(data)) as image:
        if image.format not in {"JPEG", "PNG"}:
            raise ValueError("File contents must be JPEG or PNG")
        return [_encode(image)]
