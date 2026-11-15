"""Observed spending and explicit scenarios; never infer unrecorded purchases."""
import math
import pandas as pd


def spending_profiles(lines):
    profiles = []
    for buyer, group in lines.dropna(subset=['customer_id']).groupby('customer_id'):
        values = pd.to_numeric(group.line_total, errors='coerce')
        valid = values.notna() & values.map(lambda v: math.isfinite(v) if pd.notna(v) else False) & (values >= 0)
        g = group.assign(_spend=values.where(valid), _month=group.timestamp.dt.strftime('%Y-%m'))
        monthly = []
        for month, rows in g.groupby('_month'):
            monthly.append(dict(month=month, spend=round(float(rows._spend.sum()), 2),
                                priced=int(rows._spend.notna().sum()), lines=len(rows)))
        categories = []
        for category, rows in g.groupby('category', dropna=False):
            categories.append(dict(name=str(category).replace('_', ' ').capitalize(),
                                   spend=round(float(rows._spend.sum()), 2)))
        profiles.append(dict(id=str(buyer), total=round(float(g._spend.sum()), 2),
                             priced=int(valid.sum()), lines=len(g), trips=int(g.transaction_id.nunique()),
                             start=g.timestamp.min().date().isoformat(), end=g.timestamp.max().date().isoformat(),
                             months=monthly, categories=sorted(categories,key=lambda x:-x['spend'])))
    return profiles
