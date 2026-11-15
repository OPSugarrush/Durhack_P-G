from decimal import Decimal, ROUND_HALF_UP
from .models import Receipt


def check_receipt(receipt: Receipt, tolerance=Decimal("0.02")) -> list[str]:
    issues = list(receipt.uncertainty)
    products = [e for e in receipt.entries if e.kind == "product"]
    if not products:
        issues.append("No purchased products identified")
    if receipt.priced_line_count is not None and receipt.priced_line_count != len(products):
        issues.append(f"Review item count: {receipt.priced_line_count} detected priced lines, {len(products)} product rows")
    if products and receipt.total is not None and all(e.amount is not None for e in products):
        line_sum = sum((Decimal(str(e.amount)) for e in products), Decimal(0))
        difference = line_sum - Decimal(str(receipt.total))
        if difference:
            issues.append(f"Review net product sum: {line_sum:.2f}, printed total {receipt.total:.2f}, difference {difference:+.2f}. Check missing items or separate adjustments.")
    for field in ("store_name", "store_address", "date", "time", "currency", "total"):
        if getattr(receipt, field) is None:
            issues.append(f"Missing receipt {field}")
    for index, e in enumerate(receipt.entries, 1):
        if e.uncertainty:
            issues.append(f"Entry {index}: {e.uncertainty}")
        if e.kind == "product":
            for field in ("description", "quantity", "unit_price", "amount"):
                if getattr(e, field) is None:
                    issues.append(f"Entry {index}: missing {field}")
            if e.quantity is not None and e.quantity <= 0:
                issues.append(f"Entry {index}: non-positive quantity; review return/void")
            if all(v is not None for v in (e.quantity, e.unit_price, e.amount)):
                expected = (Decimal(str(e.quantity)) * Decimal(str(e.unit_price))).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP) + Decimal(str(e.promotion_amount or 0))
                if abs(expected - Decimal(str(e.amount))) > tolerance:
                    issues.append(f"Entry {index}: quantity × unit price differs from line total (possibly promotion)")
            if e.affects_total is not True:
                issues.append(f"Entry {index}: product contribution to total needs review")
        if e.kind == "discount" and e.amount is not None and e.amount > 0:
            issues.append(f"Entry {index}: discount must be negative")
    contributing = [e for e in receipt.entries if e.affects_total is True]
    unknown = any(e.affects_total is None or
                  (e.affects_total and e.amount is None) for e in receipt.entries)
    if unknown or not products or receipt.total is None:
        issues.append("Receipt arithmetic unverifiable: missing amounts or unclear contributions")
    else:
        summed = sum((Decimal(str(e.amount)) for e in contributing), Decimal(0))
        difference = summed - Decimal(str(receipt.total))
        if abs(difference) > tolerance:
            issues.append(f"Receipt total mismatch: entries {summed:.2f}, printed {receipt.total:.2f}, difference {difference:.2f}")
    return issues
