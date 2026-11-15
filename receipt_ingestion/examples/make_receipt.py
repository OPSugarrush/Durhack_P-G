"""Recreate the synthetic visual fixture; no API is called."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def main():
    image = Image.new("RGB", (700, 900), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=22)
    text = """EXAMPLE MARKET - SYNTHETIC TEST
12 Example Street
2026-11-14  10:30

OAT DRINK 1L
2 x 2.00                       4.00
APPLES KG
0.500 kg @ 4.00/kg              2.00
BASKET COUPON                 -0.50

TOTAL GBP                      5.50
VAT INCLUDED                   0.20
CARD                           5.50

Thank you
"""
    draw.multiline_text((35, 40), text, font=font, fill="black", spacing=15)
    image.save(Path(__file__).with_name("demo_receipt.png"))

if __name__ == "__main__":
    main()
