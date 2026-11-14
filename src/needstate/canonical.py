"""Stable line-item contract, independent of source column names."""
LINE_COLUMNS = [
    "line_id", "transaction_id", "customer_id", "retailer_id", "store_id",
    "timestamp", "raw_product_text", "quantity", "unit_price", "line_total",
    "promotion_label", "promotion_flag", "line_number", "receipt_total", "image_ref",
]
REQUIRED_LINE_COLUMNS = ["transaction_id", "timestamp", "raw_product_text"]
