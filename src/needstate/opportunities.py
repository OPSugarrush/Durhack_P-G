"""Portfolio decisions based on observed category trips, not assumed market revenue."""
import hashlib
import numpy as np
import pandas as pd
from needstate.product_intel.portfolio import PortfolioLens


def portfolio_opportunities(lines, hierarchy):
    lens = PortfolioLens(name='P&G', focal_owners=['P&G'])
    relevant = set(hierarchy.loc[lens.in_portfolio(hierarchy), 'category'])
    results = []
    for category, group in lines.dropna(subset=['customer_id']).groupby('category'):
        if category == 'unclassified':
            continue
        # Unknown brands cannot be treated as competing brands.
        known = group.groupby('transaction_id').brand.apply(lambda s: s.notna().all())
        g = group[group.transaction_id.isin(known[known].index)].copy()
        g['_portfolio'] = lens.in_portfolio(g)
        trips = g.groupby(['customer_id', 'transaction_id']).agg(date=('timestamp','min'), hit=('_portfolio','max')).reset_index()
        if trips.empty:
            continue
        boundary = trips.date.max().to_period('M').start_time
        train, test = trips[trips.date < boundary], trips[trips.date >= boundary]
        counts = train.groupby('customer_id').hit.agg(['sum','count'])
        eligible = counts.index[counts['count'] >= 2]
        # One held-out next category trip per buyer; no future features.
        test = test[test.customer_id.isin(eligible)].sort_values('date').drop_duplicates('customer_id')
        forecast = None
        if len(test) >= 20 and train.date.dt.to_period('M').nunique() >= 3:
            baseline = float(train.hit.mean())
            p = np.array([(counts.loc[b,'sum'] + 2*baseline)/(counts.loc[b,'count']+2) for b in test.customer_id])
            y = test.hit.to_numpy(dtype=float)
            model_error = float(np.mean((p-y)**2))
            base_error = float(np.mean((baseline-y)**2))
            use_personal = model_error < base_error
            all_counts = trips.groupby('customer_id').hit.agg(['sum','count'])
            all_counts = all_counts[all_counts['count'] >= 2]
            rate = float(trips.hit.mean())
            estimates = (all_counts['sum']+2*rate)/(all_counts['count']+2) if use_personal else pd.Series(rate,index=all_counts.index)
            forecast = dict(rate=round(float(estimates.mean()*100),1), buyers=len(estimates),
                            method='History baseline' if use_personal else 'Category baseline',
                            validation_buyers=len(test), brier=model_error if use_personal else base_error,
                            baseline_brier=base_error, cutoff=str(boundary.date()),
                            target='P&G on the next observed category trip')
        switches = 0
        for _, history in trips.sort_values('date').groupby('customer_id'):
            values = history.hit.tolist()
            switches += len(values)>=4 and all(values[-4:-2]) and not any(values[-2:])
        results.append(dict(id=hashlib.sha256(str(category).encode()).hexdigest()[:12],
            category=str(category).replace('_',' ').capitalize(), relevant=category in relevant,
            buyers=int(trips.customer_id.nunique()), coverage=round(100*len(g)/len(group)),
            switches=int(switches), forecast=forecast,
            title='Investigate portfolio repeat loss' if switches else 'Review portfolio repeat purchasing'))
    return sorted(results,key=lambda r:(not r['relevant'],-r['switches'],-r['buyers']))
