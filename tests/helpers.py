"""Synthetic fixtures. Dataset-specific numbers live ONLY in tests (never in src)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from needstate.baskets.construction import BasketMatrix


def synthetic_bm(
    n_consumers: int = 120,
    n_products: int = 30,
    receipts_per: int = 10,
    n_months: int = 6,
    seed: int = 0,
    bundle: tuple[int, int] | None = None,
    bundle_rate: float = 0.0,
    trend_product: int | None = None,
    trend_strength: float = 0.0,
) -> BasketMatrix:
    """Consumers have persistent personal baskets (the confound) and varying receipt sizes."""
    rng = np.random.default_rng(seed)
    rows, cons, months = [], [], []
    for c in range(n_consumers):
        fav = rng.random(n_products) ** 3          # personal product propensities (skewed)
        fav = fav / fav.max() * 0.7
        for _ in range(receipts_per):
            size_mult = rng.uniform(0.4, 1.6)      # big shops vs small shops
            m = int(rng.integers(0, n_months))
            p = np.clip(fav * size_mult, 0, 0.95)
            if trend_product is not None:
                p[trend_product] = np.clip(p[trend_product] + trend_strength * m / (n_months - 1), 0, 1)
            x = (rng.random(n_products) < p).astype(np.uint8)
            if bundle and rng.random() < bundle_rate:
                x[bundle[0]] = x[bundle[1]] = 1
            rows.append(x); cons.append(c); months.append(m)
    X = np.array(rows)
    receipts = pd.DataFrame({"transaction_id": [f"R{i}" for i in range(len(X))], "customer_id": [f"C{c}" for c in cons]})
    return BasketMatrix("family", [f"p{i}" for i in range(n_products)], receipts, X, np.array(months), [f"m{i}" for i in range(n_months)], np.array(cons))


def mini_lines() -> pd.DataFrame:
    """Tiny canonical line table with OCR variants, abbreviations and truncation."""
    names = [
        "ARIEL ORIG WASH LIQ 24 W", "AR1EL 0RIG WASH LIQ 24 W", "ARIEL ORIG WASHING LIQUID 24 W",
        "CUSHELLE ORIG T/TISSUE 4 ROLLS", "CUSHELLE ORIG TOILET TISSUE 4 ROL",
        "TILDA PURE BASMATI RICE 1KG", "TILDA MICROWAVE BASMATI RICE 250G",
    ]
    rows = []
    for i, n in enumerate(names * 3):
        rows.append(dict(line_id=f"L{i}", transaction_id=f"T{i // 3}", customer_id=f"C{i % 2}", retailer_id="X", store_id=None,
                         timestamp=pd.Timestamp("2026-04-01") + pd.Timedelta(days=i), raw_product_text=n, quantity=1,
                         unit_price=2.0, line_total=2.0, promotion_label=None, promotion_flag=pd.NA, line_number=i % 3 + 1,
                         receipt_total=None, image_ref=None))
    return pd.DataFrame(rows)
