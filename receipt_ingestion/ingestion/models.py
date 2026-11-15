from datetime import date, time
from typing import Literal
from pydantic import BaseModel, ConfigDict, field_validator
import math


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Entry(StrictModel):
    promotion_amount: float | None = None
    kind: Literal["product", "discount", "subtotal", "tax", "payment", "other"]
    description: str | None
    quantity: float | None
    unit_price: float | None
    amount: float | None
    promotion: str | None
    # True only if this amount contributes separately to the grand total.
    affects_total: bool | None
    uncertainty: str | None

    @field_validator("quantity", "unit_price", "amount", "promotion_amount")
    @classmethod
    def finite(cls, value):
        if value is not None and not math.isfinite(value):
            raise ValueError("Numbers must be finite")
        return value


class Receipt(StrictModel):
    priced_line_count: int | None = None
    raw_ocr_text: str | None = None
    store_name: str | None
    store_address: str | None
    date: date | None
    time: time | None
    currency: str | None
    total: float | None
    entries: list[Entry]
    uncertainty: list[str]

    @field_validator("total")
    @classmethod
    def finite(cls, value):
        return Entry.finite(value)
