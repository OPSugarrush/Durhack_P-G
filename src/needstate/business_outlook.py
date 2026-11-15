"""Descriptive category priorities and conservative observed brand histories."""
import pandas as pd
import numpy as np
from collections import defaultdict
from needstate.evidence import supported_change


def _brand_histories(group):
    """Same per-buyer rules using receipt sets, without thousands of tiny frames."""
    records = list(group[['timestamp','transaction_id','brand','owner','retailer_id','recent']].itertuples(index=False, name=None))
    histories = []
    for buyer, positions in group.groupby('customer_id').indices.items():
        rows = [records[i] for i in positions]
        trips = [set(), set()]
        brands = [defaultdict(set), defaultdict(set)]
        owners = defaultdict(set)
        shops = [set(), set()]
        all_known = True
        for timestamp, tid, brand, owner, retailer, recent in rows:
            period = int(recent)
            trips[period].add(tid)
            if pd.notna(brand):
                brands[period][brand].add(tid)
                if pd.notna(owner):
                    owners[brand].add(owner)
            else:
                all_known = False
            if pd.notna(retailer):
                shops[period].add(retailer)
        early, late = brands
        status, old, new = 'Insufficient history', None, None
        if min(map(len, trips)) >= 2 and all_known:
            if len(early) == len(late) == 1 and next(iter(early)) == next(iter(late)):
                status = 'Consistent purchasing'
            elif len(early) == len(late) == 1 and len(next(iter(early.values()))) >= 2 and len(next(iter(late.values()))) >= 2:
                status, old, new = 'Possible switch', str(next(iter(early))), str(next(iter(late)))
            else:
                added = [len(tids) for brand, tids in late.items() if brand not in early]
                status = 'Repeated trial' if added and max(added) >= 2 else 'First observed trial' if added else 'Mixed-brand purchasing'
        def owner_of(brand):
            values = owners.get(brand, ())
            return str(next(iter(values))) if len(values) == 1 else None
        old_owner, new_owner = owner_of(old), owner_of(new)
        # Match pandas' existing quicksort tie ordering, including same-date trips.
        order = np.argsort(np.array([r[0].asm8 for r in rows]), kind='quicksort')
        timeline = {}
        for i in order:
            timestamp, tid, brand, *_ = rows[i]
            entry = timeline.setdefault(tid, dict(receipt=str(tid), date=timestamp.date().isoformat(), brands=set()))
            if pd.notna(brand):
                entry['brands'].add(brand)
        histories.append(dict(buyer=str(buyer), status=status, previous=old, current=new,
                              owner_movement=('Same owner' if old_owner == new_owner else 'Different owners') if old_owner and new_owner else 'Ownership unresolved',
                              retailer_changed=shops[0] != shops[1],
                              timeline=[dict(entry, brands=sorted(entry['brands'])) for entry in timeline.values()]))
    return histories


def category_reach(lines, boundary):
    recent = lines.dropna(subset=['customer_id'])
    recent = recent[recent.timestamp.dt.strftime('%Y-%m-%d') >= boundary]
    total = int(recent.customer_id.nunique())
    return sorted([dict(name=str(cat).replace('_',' ').capitalize(), buyers=int(g.customer_id.nunique()),
                        total=total, reach=100*int(g.customer_id.nunique())/total)
                   for cat,g in recent.groupby('category') if cat!='unclassified' and total],
                  key=lambda c:(-c['reach'],c['name']))


def business_outlook(lines, boundary, evidence):
    data = lines.dropna(subset=['customer_id']).copy()
    data['recent'] = data.timestamp.dt.strftime('%Y-%m-%d') >= boundary
    data['_month'] = data.timestamp.dt.strftime('%Y-%m')
    trips = data.drop_duplicates('transaction_id')
    counts = trips.groupby(['customer_id', 'recent']).size().unstack(fill_value=0).reindex(columns=[False, True], fill_value=0)
    eligible = counts.index[counts.min(axis=1) >= 2]
    data = data[data.customer_id.isin(eligible)]
    months_all = pd.period_range(trips.timestamp.min(), trips.timestamp.max(), freq='M').astype(str) if len(trips) else []
    month_totals = trips[trips.customer_id.isin(eligible)].groupby('_month').transaction_id.nunique().to_dict()
    categories = []
    for category, g in data.groupby('category'):
        if category == 'unclassified':
            continue
        name = category.replace('_', ' ').capitalize()
        ev = evidence.get(name, {})
        supported = supported_change(ev)
        period_hits = g.drop_duplicates('transaction_id').groupby(['customer_id','recent']).size().unstack(fill_value=0).reindex(index=eligible,columns=[False,True],fill_value=0)
        observed_change = 100*((period_hits[True]/counts.loc[eligible,True])-(period_hits[False]/counts.loc[eligible,False])).mean()
        change = round(float(observed_change),1)
        status = ('Prioritise a test' if change > 0 else 'Investigate a decline') if supported else ('Insufficient evidence' if len(eligible) < 20 or g.customer_id.nunique() < 10 else 'Watch' if abs(change) >= 3 else 'Maintain and understand')
        actions = {'Prioritise a test': 'Investigate the products driving growth, then test availability or a complementary offer with a comparison group.', 'Investigate a decline': 'Check retailer coverage and availability before testing a retention or assortment change.', 'Watch': 'Collect another period of receipts and check whether this movement persists.', 'Maintain and understand': 'Study repeat buyers and basket companions before changing an established offer.', 'Insufficient evidence': 'Build more comparable buyer histories before allocating investment on this signal.'}
        months = []
        month_hits = g.groupby('_month').transaction_id.nunique().to_dict()
        for month in months_all:
            months.append(dict(month=month, trips=int(month_hits.get(month, 0)), total=int(month_totals.get(month, 0))))
        movements = {}
        drivers = g[g.recent].groupby('raw_product_text').transaction_id.nunique().sort_values(ascending=False).head(3) if 'raw_product_text' in g else pd.Series(dtype=int)
        cat_counts = g.drop_duplicates('transaction_id').groupby(['customer_id','recent']).size().unstack(fill_value=0).reindex(columns=[False,True],fill_value=0)
        both = cat_counts.index[cat_counts.min(axis=1) >= 2]
        for level in ['brand', 'owner']:
            rows = []
            # Equal customer weights; within-category trips are the denominator.
            for entity, part in g.dropna(subset=[level]).groupby(level):
                rates = []
                for period in [False, True]:
                    hits = part[part.recent.eq(period)].groupby('customer_id').transaction_id.nunique().reindex(both,fill_value=0)
                    rates.append(float((hits/cat_counts.loc[both,period]).mean()*100) if len(both) else None)
                rows.append(dict(name=str(entity), earlier=rates[0], recent=rates[1], buyers=len(both)))
            movements[level] = rows
        histories = _brand_histories(g)
        categories.append(dict(name=name,change=change,status=status,action=actions[status],drivers=[dict(name=str(k),trips=int(v)) for k,v in drivers.items()],buyers=int(g.customer_id.nunique()),comparable=len(eligible),months=months,
            brand_coverage=round(float(g.brand.notna().mean()*100)),owner_coverage=round(float(g.owner.notna().mean()*100)),movements=movements,histories=histories))
    return sorted(categories,key=lambda c:(c['status']!='Prioritise a test',-c['change']))
