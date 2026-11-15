"""CPU OCR with package-bundled ONNX models and geometric row reconstruction."""
import base64
from dataclasses import dataclass
from functools import lru_cache
import io
from pathlib import Path
from PIL import Image, ImageOps
import numpy as np
import re


@dataclass(frozen=True)
class OCRLine:
    text: str
    confidence: float = 1.0
    page: int = 1


@lru_cache(maxsize=1)
def get_engine():
    import rapidocr_onnxruntime
    from rapidocr_onnxruntime import RapidOCR
    directory = Path(rapidocr_onnxruntime.__file__).parent / "models"
    def model(suffix):
        matches = list(directory.glob(f"*{suffix}*.onnx"))
        if len(matches) != 1:
            raise RuntimeError("OCR models missing. Reinstall requirements.txt into .venv.")
        return str(matches[0])
    return RapidOCR(det_model_path=model("det"), cls_model_path=model("cls"),
                    rec_model_path=model("rec"), text_score=0.1,
                    intra_op_num_threads=2, inter_op_num_threads=2)


def group_rows(result, page=1):
    """Merge price and description boxes on the same baseline, left to right."""
    tokens = []
    for box, text, confidence in result or []:
        xs, ys = zip(*box)
        tokens.append((min(xs), sum(ys)/len(ys), max(ys)-min(ys), str(text), float(confidence)))
    groups = []
    for token in sorted(tokens, key=lambda t: (t[1], t[0])):
        candidates = [g for g in groups if abs(g[0][1]-token[1]) <= 0.45*min(g[0][2], token[2])]
        if candidates:
            min(candidates, key=lambda g: abs(g[0][1]-token[1])).append(token)
        else:
            groups.append([token])
    return [OCRLine("  ".join(t[3] for t in sorted(group)),
                    min(t[4] for t in group), page) for group in groups]


def read_images(images):
    engine = get_engine()
    lines = []
    for page, data_url in enumerate(images, 1):
        data = base64.b64decode(data_url.split(",", 1)[1], validate=True)
        with Image.open(io.BytesIO(data)) as image:
            image = ImageOps.autocontrast(ImageOps.grayscale(image))
            if image.width < 1000:
                scale = min(2, 1000 / image.width)
                image = image.resize((int(image.width*scale), int(image.height*scale)))
            detector = engine.text_det.postprocess_op
            incoming = (detector.box_thresh, detector.unclip_ratio, engine.text_score)
            # Prefer the dark-ink pass when it exposes a receipt's priced rows
            # and footer. Local background subtraction suppresses reverse print.
            import cv2
            gray = np.asarray(image)
            background = cv2.GaussianBlur(gray, (0, 0), max(5, image.width / 130))
            ink = background.astype("float32") - gray
            clean = np.clip(255 - (ink - 32) * 14, 0, 255).astype("uint8")
            rgb = cv2.cvtColor(clean, cv2.COLOR_GRAY2RGB)
            cleaned, _ = engine(rgb, box_thresh=.25, unclip_ratio=1.3)
            aligned = align_price_column(cleaned or [], rgb, engine)
            if aligned is None:
                # RapidOCR persists per-call thresholds. The fallback must use
                # the settings the original first pass would have seen, then
                # leave the engine in the same state as the dark-ink pass.
                outgoing = (detector.box_thresh, detector.unclip_ratio, engine.text_score)
                detector.box_thresh, detector.unclip_ratio, engine.text_score = incoming
                try:
                    result, _ = engine(np.asarray(image.convert("RGB")))
                finally:
                    detector.box_thresh, detector.unclip_ratio, engine.text_score = outgoing
        lines.extend(group_rows(aligned if aligned is not None else result, page))
    return lines


def align_price_column(boxes, image, engine):
    """Pair separate price boxes with labels using order and bounded geometry."""
    def center(box):
        return sum(point[1] for point in box) / 4

    def left(box):
        return min(point[0] for point in box)

    prices = sorted((b for b in boxes if re.fullmatch(r"-?[£€$]?\d+[.,]\d{2}", b[1].strip())),
                    key=lambda b: center(b[0]))
    labels = sorted((b for b in boxes if b not in prices), key=lambda b: center(b[0]))
    if len(prices) < 4:
        return None
    # Only activate order-based alignment for a clearly repeated quantity
    # column and a recognized footer with a complete set of amount boxes.
    qty = re.compile(r"^\s*\d+\s+[A-Za-z]")
    footer = re.compile(r"^(?:subtotal|savings|promotions|total|cash|change due|card)\b", re.I)
    footer_rows = [b for b in labels if footer.match(b[1])]
    if not any(re.match(r"^total\b", b[1], re.I) for b in footer_rows):
        return None
    first_footer = center(footer_rows[0][0])
    items = [b for b in labels if center(b[0]) < first_footer and qty.match(b[1])]
    if len(items) < 3:
        return None
    x_qty = float(np.median([left(b[0]) for b in items]))
    height = float(np.median([max(p[1] for p in b[0])-min(p[1] for p in b[0]) for b in items]))
    candidates = []
    for b in labels:
        box, text, score = b
        if qty.match(text) and abs(left(box)-x_qty) < height:
            candidates.append(b)
        elif footer.match(text) or re.match(r"^special\s+offer\b", text, re.I):
            candidates.append(b)
        elif (x_qty + height*.35 < left(box) < x_qty + height*1.25
              and center(items[0][0]) < center(box) < first_footer
              and any(abs(center(box)-center(p[0])) < height*.65 for p in prices)):
            # Detector can miss the isolated quantity glyph. Read the margin
            # as a separate image and require a confident numeric result.
            y = (box[0][1]+box[3][1])/2
            crop = image[max(0, int(y-height*.5)):int(y+height*.5),
                         max(0,int(x_qty-height*.35)):int(left(box)-height*.15)]
            if crop.size:
                values, _ = engine(crop, use_det=False)
                if values and re.fullmatch(r"\d+", values[0][0]) and values[0][1] >= .8:
                    b[1] = values[0][0] + " " + text.strip()
                    candidates.append(b)
    if len(candidates) != len(prices):
        return None
    if any(abs(center(label[0])-center(price[0])) > height*1.2
           or left(price[0]) <= left(label[0]) for label, price in zip(candidates, prices)):
        return None
    for label, price in zip(candidates, prices):
        label[1] += "  " + price[1]
        label[2] = min(label[2], price[2])
    return labels
