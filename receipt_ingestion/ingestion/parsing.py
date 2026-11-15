"""Human edits pass through the same schema as model extraction."""
import pandas as pd
from .models import Receipt


def edited_receipt(original: Receipt, metadata: dict, table: pd.DataFrame) -> Receipt:
    entries = table.astype(object).where(pd.notna(table), None).to_dict("records")
    payload = original.model_dump(mode="json")
    payload.update(metadata)
    payload["entries"] = entries
    for key in ("date", "time", "store_name", "store_address", "currency"):
        if payload[key] == "":
            payload[key] = None
    return Receipt.model_validate(payload)
