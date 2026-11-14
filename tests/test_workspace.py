import json
import threading
import time
from io import BytesIO
from urllib.request import Request, urlopen

import pandas as pd
import pytest
from openpyxl import Workbook

from needstate.workspace import analyse_lines, behaviour, combine, config, workbook
from needstate.webapp import demo, server


@pytest.mark.parametrize("counts,label", [
    ((0,2,4,4),"Newly observed"), ((2,0,4,4),"No recent purchase"),
    ((1,3,4,4),"More frequent"), ((3,1,4,4),"Less frequent"),
    ((3,3,4,4),"Established routine"), ((1,1,4,4),"Occasional purchase"),
    ((0,2,1,4),"Limited history")])
def test_history_requires_observation(counts,label):
    assert behaviour(*counts) == label


def encoded(rows):
    book = Workbook()
    sheet = book.active
    sheet.title = "April receipts"
    sheet.append(["Receipt ID","Consumer ID","Date","Product Name","Line Number","Quantity","Unit Price","Line Total"])
    for row in rows:
        sheet.append(row)
    buffer = BytesIO()
    book.save(buffer)
    return buffer.getvalue()


ROW = ["001","07","2026-04-01","ARIEL WASHING LIQUID",1,1,2,2]


def test_exact_repeat_preserves_identifiers():
    frame,skip = workbook(encoded([ROW,ROW]),config().mapping)
    assert len(frame)==1 and skip==1 and frame.transaction_id.iloc[0]=="001"
    merged,count=combine(frame,frame)
    assert len(merged)==1 and count==1


def test_conflicting_number_in_workbook():
    other = ROW.copy()
    other[3]="DIFFERENT"
    with pytest.raises(ValueError,match="Conflicting"):
        workbook(encoded([ROW,other]),config().mapping)


def test_partial_overlap_rejects_batch():
    cfg=config()
    first,_=workbook(encoded([ROW]),cfg.mapping)
    other=ROW.copy()
    other[4]=2
    extended,_=workbook(encoded([ROW,other]),cfg.mapping)
    with pytest.raises(ValueError,match="overlaps"):
        combine(first,extended)
    assert len(first)==1


def test_receipt_without_buyer_still_supports_mission():
    cfg=config()
    frame=demo(cfg)
    frame["customer_id"]=pd.NA
    r=analyse_lines(frame,cfg)
    assert r["buyers"]==0 and r["findings"]
    assert all(f["buyers"]==0 for f in r["findings"])


def test_http_workbook_and_demo():
    cfg=config()
    data=cfg.input_path.read_bytes() if cfg.input_path.exists() else encoded([ROW])
    http=server(0)
    threading.Thread(target=http.serve_forever,daemon=True).start()
    base=f"http://127.0.0.1:{http.server_port}/"
    def api(path,body=None):
        req=Request(base+"api/"+path,data=body,headers={"X-Workspace":http.store.token})
        with urlopen(req,timeout=5) as res:
            return json.load(res)
    def finish():
        deadline=time.monotonic()+120
        while time.monotonic()<deadline:
            s=api("state")
            if s["phase"]!="working":
                return s
            time.sleep(.2)
        pytest.fail("Import exceeded two minutes")
    try:
        for asset in ("","app.js","style.css"):
            with urlopen(base+asset,timeout=5) as res:
                assert res.status==200
        api("sample",b"")
        assert finish()["sample"]
        assert api("findings")["total"]==64
        api("import",data)
        assert finish()["phase"]=="ready"
        r=api("findings")
        assert r["total"]==http.store.lines.transaction_id.nunique()
        assert any(f["kind"]=="Shopping mission" for f in r["findings"])
        assert api("evidence?finding=0&buyer=0")["receipts"][0]["parts"]
        api("import",b"invalid")
        assert finish()["previous"] and api("findings")==r
    finally:
        http.shutdown()
        http.server_close()
