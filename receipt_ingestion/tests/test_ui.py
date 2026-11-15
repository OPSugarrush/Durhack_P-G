from pathlib import Path
from streamlit.testing.v1 import AppTest


def test_offline_demo():
    app = AppTest.from_file(str(Path(__file__).parents[1]/"app.py")).run()
    assert not app.exception
    next(b for b in app.button if b.label.startswith("Load offline")).click().run()
    assert not app.exception
    assert len(app.dataframe) >= 1
