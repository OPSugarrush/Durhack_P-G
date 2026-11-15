"""Fallback recognition retains the legacy engine settings and output."""
import base64
from io import BytesIO
from types import SimpleNamespace

import pytest

pytest.importorskip('rapidocr_onnxruntime')
from PIL import Image
from needstate_receipt_ingestion import ocr


@pytest.mark.parametrize('aligned', [None, []])
def test_deferred_normal_pass_preserves_thresholds(monkeypatch, aligned):
    class Engine:
        def __init__(self):
            self.text_det = SimpleNamespace(postprocess_op=SimpleNamespace(box_thresh=.5, unclip_ratio=1.6))
            self.text_score = .1
            self.calls = []

        def __call__(self, image, **kwargs):
            det = self.text_det.postprocess_op
            if kwargs:
                det.box_thresh = kwargs.get('box_thresh', .5)
                det.unclip_ratio = kwargs.get('unclip_ratio', 1.6)
                self.text_score = kwargs.get('text_score', .5)
            self.calls.append((det.box_thresh, det.unclip_ratio, self.text_score))
            return [([[0, 0], [20, 0], [20, 10], [0, 10]], 'MILK 1.00', .99)], None

    engine = Engine()
    monkeypatch.setattr(ocr, 'get_engine', lambda: engine)
    monkeypatch.setattr(ocr, 'align_price_column', lambda *args: aligned)
    raw = BytesIO()
    Image.new('RGB', (20, 20), 'white').save(raw, format='PNG')
    page = 'data:image/png;base64,' + base64.b64encode(raw.getvalue()).decode()
    result = ocr.read_images([page, page])
    cleaned = (.25, 1.3, .5)
    if aligned is None:
        assert engine.calls == [cleaned, (.5, 1.6, .1), cleaned, cleaned]
        assert [line.text for line in result] == ['MILK 1.00', 'MILK 1.00']
    else:
        assert engine.calls == [cleaned, cleaned]
        assert result == []
    det = engine.text_det.postprocess_op
    assert (det.box_thresh, det.unclip_ratio, engine.text_score) == cleaned
