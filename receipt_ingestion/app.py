import hashlib
import json
from pathlib import Path
import pandas as pd
import streamlit as st
from ingestion.models import Receipt, Entry
from ingestion.images import prepare_images
from ingestion.extraction import extract_receipt
from ingestion.parsing import edited_receipt
from ingestion.validation import check_receipt
from ingestion.export import new_id, dataframe, excel_bytes, json_bytes

st.set_page_config(page_title="NeedState Receipt Ingestion", layout="wide")
st.title("Receipt → structured data")
st.caption("Local OCR · No API key · Upload one receipt, review, then export for NeedState Engine.")
if "consumer_id" not in st.session_state:
    st.session_state.consumer_id = new_id("C")
if st.button("Generate new Consumer ID"):
    st.session_state.consumer_id = new_id("C")
consumer = st.text_input("Pseudonymous Consumer ID", key="consumer_id")
st.caption("Reuse an ID for repeat visits. Do not enter a name, email or loyalty number.")
upload = st.file_uploader("Receipt (JPG, PNG, PDF; maximum 20 MB / 5 pages)",
                          type=["jpg", "jpeg", "png", "pdf"])
if st.button("Extract receipt locally", disabled=upload is None):
    st.session_state.pop("result", None)
    try:
        with st.spinner("Reading receipt…"):
            raw = upload.getvalue()
            pages = prepare_images(raw, upload.name)
            receipt = extract_receipt(pages)
        st.session_state.result = dict(original=receipt, receipt_id=new_id("R"),
            filename=upload.name, digest=hashlib.sha256(raw).hexdigest(), pages=pages, demo=False)
    except Exception as error:
        st.error(f"Local extraction failed ({type(error).__name__}): {error}. Check the image and run .venv\\Scripts\\python.exe -m pip install -r requirements.txt if dependencies are missing.")
if st.button("Load offline demo"):
    fixture = Path(__file__).parent / "examples" / "receipt.json"
    st.session_state.result = dict(original=Receipt.model_validate_json(fixture.read_text()),
        receipt_id=new_id("R"), filename="demo_receipt.png", digest=None,
        pages=prepare_images(fixture.with_name("demo_receipt.png").read_bytes(), "demo_receipt.png"), demo=True)

if "result" in st.session_state:
    result = st.session_state.result
    original = result["original"]
    key = result["receipt_id"]
    st.subheader(f"Review: {result['filename']}")
    st.caption(f"Receipt ID: {key}")
    if result["demo"]:
        st.info("Synthetic demo with prefilled extraction. Upload its image to try the local OCR engine.")
    elif upload is None or hashlib.sha256(upload.getvalue()).hexdigest() != result["digest"]:
        st.warning("The selected upload differs from this review. Extract it to start a new review.")
    with st.expander("Receipt images"):
        for page in result["pages"]:
            st.image(page)
    if original.raw_ocr_text:
        with st.expander("Original OCR text and confidence"):
            st.text(original.raw_ocr_text)
    left, right = st.columns(2)
    metadata = {}
    with left:
        for field, label in [("store_name", "Store name"), ("store_address", "Store address"),
                             ("date", "Date (YYYY-MM-DD; blank if unknown)")]:
            metadata[field] = st.text_input(label, str(getattr(original, field) or ""), key=key+field)
    with right:
        for field, label in [("time", "Time (HH:MM:SS; blank if unknown)"), ("currency", "Currency")]:
            metadata[field] = st.text_input(label, str(getattr(original, field) or ""), key=key+field)
        total = st.text_input("Receipt total (blank if unknown)",
                              "" if original.total is None else str(original.total), key=key+"total")
    st.write("Correct entries below. Only rows marked product enter the Excel export.")
    st.caption("affects_total: checked = add separately; unchecked = already included or informational; blank = unknown. Discounts use negative amounts.")
    source = pd.DataFrame([e.model_dump() for e in original.entries], columns=list(Entry.model_fields))
    for column in ("quantity", "unit_price", "amount", "promotion_amount"):
        source[column] = source[column].astype("Float64")
    source["affects_total"] = source["affects_total"].astype("boolean")
    table = st.data_editor(source, num_rows="dynamic", key=key+"entries", hide_index=True,
        column_config={"kind": st.column_config.SelectboxColumn("Entry type", options=[
            "product", "discount", "subtotal", "tax", "payment", "other"], required=True)})
    notes = st.text_area("Receipt uncertainty notes (one per line; clear resolved notes)",
                         "\n".join(original.uncertainty), key=key+"notes")
    try:
        metadata["total"] = float(total) if total.strip() else None
        metadata["uncertainty"] = [line for line in notes.splitlines() if line.strip()]
        current = edited_receipt(original, metadata, table)
        issues = check_receipt(current)
        if issues:
            st.warning("Review required:\n\n" + "\n".join("- " + i for i in issues))
        else:
            st.success("Arithmetic and required-field checks passed. Verify against the image.")
        st.subheader("Exact workbook rows")
        st.dataframe(dataframe(current, consumer, key, result["filename"]), hide_index=True)
        review_hash = hashlib.sha256((current.model_dump_json()+consumer).encode()).hexdigest()[:16]
        accepted = st.checkbox("I reviewed the receipt and accept any listed uncertainties", key=key+review_hash+"reviewed")
        args = (current, consumer, key, result["filename"])
        disabled = not accepted or not any(e.kind == "product" for e in current.entries)
        st.download_button("Download Excel", excel_bytes(*args), file_name=f"{key}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", disabled=disabled)
        st.download_button("Download NeedState JSON", json_bytes(*args, original=original,
                           source_hash=result["digest"]), file_name=f"{key}.json",
                           mime="application/json", disabled=disabled)
    except (ValueError, TypeError) as error:
        st.error(f"Correct the edited values before exporting: {error}")
