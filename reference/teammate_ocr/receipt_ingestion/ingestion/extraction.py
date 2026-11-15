"""Local OCR -> receipt parser. No remote services or API keys."""
from .ocr import read_images
from .receipt_parser import parse_lines


def extract_receipt(images, reader=None):
    if not images:
        raise ValueError("No receipt images supplied")
    return parse_lines((reader or read_images)(images))
