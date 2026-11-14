"""Blind review of a reproducible receipt sample from a workbook."""
import argparse
import json
from itertools import combinations
from pathlib import Path

import pandas as pd

from needstate.workspace import analyse_lines, config, workbook


def review_rows(report, count):
    ids = pd.Series(sorted(report["receipts"])).sample(
        n=min(count, report["total"]), random_state=42)
    for tid in ids:
        receipt = report["receipts"][tid]
        for product in sorted(p for part in receipt["parts"] for p in part["products"]):
            yield dict(receipt=tid, product=product, group="", needs="")


def compare(report, annotations):
    results = []
    for tid, rows in annotations.groupby("receipt"):
        receipt = report["receipts"][tid]
        predicted = {p:(i, {n["label"] for n in part["needs"]} if not receipt["abstained"] else set())
                     for i,part in enumerate(receipt["parts"]) for p in part["products"]}
        if rows["group"].eq("").all():
            continue
        if (set(rows["product"]) != predicted.keys() or rows["product"].duplicated().any()
                or rows["group"].eq("").any()):
            raise ValueError(f"Complete one group per product for receipt {tid}.")
        groups = dict(zip(rows["product"], rows["group"]))
        pairs = list(combinations(groups,2))
        disagreements = [[a,b] for a,b in pairs if (groups[a]==groups[b]) != (predicted[a][0]==predicted[b][0])]
        label_diffs = []
        for row in rows.itertuples():
            labels = {v.strip() for v in row.needs.split("|") if v.strip()}
            if labels != predicted[row.product][1]:
                label_diffs.append(dict(product=row.product, reviewer=sorted(labels), engine=sorted(predicted[row.product][1])))
        results.append(dict(receipt=tid, pairs=len(pairs), grouping_disagreements=disagreements,
                            products=len(rows), label_disagreements=label_diffs))
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", type=Path)
    parser.add_argument("annotations", type=Path)
    parser.add_argument("--compare", action="store_true")
    parser.add_argument("--count", type=int, default=30)
    args = parser.parse_args()
    cfg = config()
    lines,_ = workbook(args.workbook.read_bytes(),cfg.mapping)
    report = analyse_lines(lines,cfg)
    if args.compare:
        reviews = compare(report,pd.read_csv(args.annotations,dtype=str,keep_default_na=False))
        pairs = sum(r["pairs"] for r in reviews)
        products = sum(r["products"] for r in reviews)
        print(json.dumps(dict(reviewed=len(reviews),
            pair_agreement=1-sum(len(r["grouping_disagreements"]) for r in reviews)/pairs if pairs else None,
            label_agreement=1-sum(len(r["label_disagreements"]) for r in reviews)/products if products else None,
            details=reviews),indent=2))
    else:
        pd.DataFrame(review_rows(report,args.count)).to_csv(args.annotations,mode="x",index=False)
