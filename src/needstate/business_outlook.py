"""Descriptive category priorities and conservative observed brand histories."""
import pandas as pd
from needstate.evidence import supported_change


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
    trips = data.drop_duplicates('transaction_id')
    counts = trips.groupby(['customer_id', 'recent']).size().unstack(fill_value=0).reindex(columns=[False, True], fill_value=0)
    eligible = counts.index[counts.min(axis=1) >= 2]
    data = data[data.customer_id.isin(eligible)]
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
        for month in pd.period_range(trips.timestamp.min(), trips.timestamp.max(), freq='M').astype(str):
            rows = g[g.timestamp.dt.strftime('%Y-%m').eq(month)]
            denom = trips[trips.customer_id.isin(eligible) & trips.timestamp.dt.strftime('%Y-%m').eq(month)]
            months.append(dict(month=month, trips=int(rows.transaction_id.nunique()), total=int(denom.transaction_id.nunique())))
        movements = {}
        drivers = g[g.recent].groupby('raw_product_text').transaction_id.nunique().sort_values(ascending=False).head(3) if 'raw_product_text' in g else pd.Series(dtype=int)
        for level in ['brand', 'owner']:
            rows = []
            # Equal customer weights; within-category trips are the denominator.
            cat_counts = g.drop_duplicates('transaction_id').groupby(['customer_id','recent']).size().unstack(fill_value=0).reindex(columns=[False,True],fill_value=0)
            both = cat_counts.index[cat_counts.min(axis=1) >= 2]
            for entity, part in g.dropna(subset=[level]).groupby(level):
                rates = []
                for period in [False, True]:
                    hits = part[part.recent.eq(period)].groupby('customer_id').transaction_id.nunique().reindex(both,fill_value=0)
                    rates.append(float((hits/cat_counts.loc[both,period]).mean()*100) if len(both) else None)
                rows.append(dict(name=str(entity), earlier=rates[0], recent=rates[1], buyers=len(both)))
            movements[level] = rows
        histories = []
        for buyer, rows in g.groupby('customer_id'):
            known = rows.dropna(subset=['brand'])
            early = known[~known.recent].groupby('brand').transaction_id.nunique()
            late = known[known.recent].groupby('brand').transaction_id.nunique()
            n0 = rows[~rows.recent].transaction_id.nunique()
            n1 = rows[rows.recent].transaction_id.nunique()
            status_b = 'Insufficient history'
            old, new = None, None
            if min(n0,n1) >= 2 and rows.brand.notna().all():
                if len(early)==len(late)==1 and early.index[0]==late.index[0]:
                    status_b = 'Consistent purchasing'
                elif len(early)==len(late)==1 and early.iloc[0]>=2 and late.iloc[0]>=2:
                    status_b = 'Possible switch'; old,new = str(early.index[0]),str(late.index[0])
                else:
                    added = late[~late.index.isin(early.index)]
                    status_b = 'Repeated trial' if len(added) and added.max()>=2 else 'First observed trial' if len(added) else 'Mixed-brand purchasing'
            def owner(brand):
                owners = known.loc[known.brand.eq(brand),'owner'].dropna().unique()
                return str(owners[0]) if len(owners)==1 else None
            old_owner,new_owner = owner(old),owner(new)
            shops0=set(rows.loc[~rows.recent,'retailer_id'].dropna())
            shops1=set(rows.loc[rows.recent,'retailer_id'].dropna())
            histories.append(dict(buyer=str(buyer),status=status_b,previous=old,current=new,
                owner_movement=('Same owner' if old_owner==new_owner else 'Different owners') if old_owner and new_owner else 'Ownership unresolved',
                retailer_changed=shops0!=shops1,
                timeline=[dict(receipt=str(tid),date=r.timestamp.iloc[0].date().isoformat(),brands=sorted(r.brand.dropna().unique().tolist())) for tid,r in rows.sort_values('timestamp').groupby('transaction_id',sort=False)]))
        categories.append(dict(name=name,change=change,status=status,action=actions[status],drivers=[dict(name=str(k),trips=int(v)) for k,v in drivers.items()],buyers=int(g.customer_id.nunique()),comparable=len(eligible),months=months,
            brand_coverage=round(float(g.brand.notna().mean()*100)),owner_coverage=round(float(g.owner.notna().mean()*100)),movements=movements,histories=histories))
    return sorted(categories,key=lambda c:(c['status']!='Prioritise a test',-c['change']))
