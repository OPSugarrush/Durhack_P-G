"""Conclusion-first evidence reports. All customer interpretations are observed behaviour."""
from __future__ import annotations

import hashlib
import numpy as np
import pandas as pd
from scipy.stats import binomtest

from needstate.patterns.stats import benjamini_hochberg

LABELS = {
    'ambient_meal': 'Cupboard meals & ingredients', 'dairy_chilled': 'Dairy & chilled food',
    'household_cleaning': 'Household cleaning', 'body_care': 'Body care',
    'paper_goods': 'Household paper', 'meat_fish_protein': 'Meat, fish & alternatives',
    'snacks_biscuits': 'Snacks & biscuits', 'fabric_wash': 'Laundry detergent',
    'fabric_care': 'Fabric conditioners & scent care', 'stain_removal': 'Stain removal',
    'dish_wash': 'Dishwashing', 'surface_clean': 'Surface cleaning',
    'hair_cleanse': 'Hair washing', 'oral_hygiene': 'Oral hygiene',
    'body_cleanse': 'Body cleansing', 'chilled_staple': 'Chilled essentials',
    'meal_base': 'Cooking ingredients', 'fresh_cooking': 'Fresh cooking',
    'frozen_meal': 'Frozen food', 'treat': 'Treats & snacks',
}

def label(value):
    return LABELS.get(value, str(value).replace('_', ' ').capitalize())

def evidence_label(score):
    return 'Well observed' if score >= 80 else 'Some history' if score >= 50 else 'Limited history'

def classify(a, b, n0, n1):
    """Review signals with an explicit observation floor, never intent labels."""
    if min(n0, n1) < 3:
        return 'Not enough history'
    delta = b/n1 - a/n0
    if a == 0 and b >= 2:
        return 'Newly observed'
    if a >= 2 and b == 0:
        return 'No longer observed'
    if delta >= .25 and b >= 3:
        return 'Buying more often'
    if delta <= -.25 and a >= 3:
        return 'Buying less often'
    if min(a/n0, b/n1) >= .5 and min(a,b) >= 2:
        return 'Established routine'
    if a+b >= 2:
        return 'Occasional purchase'
    return 'Little observed activity'

def build_report(pl, sources, synthetic=False):
    lines = pl.lines.copy()
    rec = lines.groupby('transaction_id', sort=False).agg(
        customer=('customer_id','first'), date=('timestamp','first'), retailer=('retailer_id','first'),
        spend=('line_total', lambda s: s.sum(min_count=1)), items=('line_id','size'))
    rec['quality'] = pl.quality.data_completeness.reindex(rec.index).fillna(0)
    cut = rec.date.min() + (rec.date.max()-rec.date.min())/2
    rec['recent'] = rec.date > cut
    known = rec.dropna(subset=['customer'])
    profiles = []; records = {}; group_info = {}
    receipt_lines = dict(tuple(lines.groupby('transaction_id', sort=False)))
    for cid, g in known.groupby('customer', sort=True):
        a = g.index[~g.recent]; b = g.index[g.recent]
        span = max(0,(g.date.max()-g.date.min()).days)
        coverage = min(1,min(len(a),len(b))/5)
        duration = min(1,span/90)
        score = round(100*g.quality.mean()*coverage*duration)
        eligible = min(len(a),len(b)) >= 3
        shops0 = set(g.loc[a,'retailer'].dropna()); shops1 = set(g.loc[b,'retailer'].dropna())
        group_info[str(cid)] = (a,b,score,eligible,shops0 == shops1 and bool(shops0))
        profile = dict(id=str(cid), receipts=len(g), earlier=len(a), recent=len(b), days=span,
                       score=score, evidence=evidence_label(score), quality=round(100*g.quality.mean()),
                       coverage=round(100*coverage), duration=round(100*duration), eligible=eligible,
                       retailer_changed=shops0 != shops1, patterns=[], changes=0,
                       cadence_days=float(g.date.sort_values().diff().dt.total_seconds().dropna().median()/86400) if len(g)>1 else None)
        profiles.append(profile)
        records[str(cid)] = []
        for tid, row in g.sort_values('date').iterrows():
            rr = receipt_lines[tid]
            records[str(cid)].append(dict(id=str(tid),date=row.date.isoformat(),retailer=str(row.retailer) if pd.notna(row.retailer) else 'Unknown retailer',
                period='Recent' if row.recent else 'Earlier',quality=round(100*row.quality),spend=row.spend,
                products=[dict(name=str(z.raw_product_text) if pd.notna(z.raw_product_text) else 'Unreadable product',
                               category=label(z.category) if pd.notna(z.category) else 'Unclassified', category_key=str(z.category),
                               function=str(z.function),brand=str(z.brand) if pd.notna(z.brand) else None,
                               quantity=z.quantity,total=z.line_total) for z in rr.itertuples()]))
    profile_map = {p['id']:p for p in profiles}
    positions = {cid:(rec.index.get_indexer(info[0]),rec.index.get_indexer(info[1])) for cid,info in group_info.items()}
    insights = []; patterns = []
    focal = pl.hierarchy.loc[pl.lens.in_portfolio(pl.hierarchy)]
    eligible_count = sum(p['eligible'] for p in profiles)
    for dimension in ['category','function']:
        entities = sorted(set(lines[dimension].dropna()) - {'unclassified'})
        presence = pd.crosstab(lines.transaction_id, lines[dimension]).reindex(index=rec.index,columns=entities,fill_value=0).gt(0)
        entity_counts = pd.crosstab(lines.transaction_id,lines[dimension]).reindex(index=rec.index,columns=entities,fill_value=0)
        presence_values = presence.to_numpy()
        item_shares = entity_counts.to_numpy()/rec['items'].to_numpy()[:,None]
        candidates = []
        for entity_index,entity in enumerate(entities):
            per = []
            for cid,(a,b,score,eligible,stable_retailer) in group_info.items():
                n0,n1 = len(a),len(b)
                indices0,indices1 = positions[cid]
                x0,x1 = int(presence_values[indices0,entity_index].sum()),int(presence_values[indices1,entity_index].sum())
                p0,p1 = x0/max(n0,1),x1/max(n1,1)
                status = classify(x0,x1,n0,n1)
                # Item-share is a descriptive sensitivity check for changing basket sizes.
                share0=float(item_shares[indices0,entity_index].mean()) if n0 else 0
                share1=float(item_shares[indices1,entity_index].mean()) if n1 else 0
                pat = dict(customer=cid,dimension=dimension,entity=entity,name=label(entity),earlier=x0,recent=x1,
                           n_earlier=n0,n_recent=n1,earlier_rate=p0,recent_rate=p1,change=p1-p0,
                           status=status,score=score,eligible=eligible,stable_retailer=stable_retailer,item_share_change=share1-share0)
                if x0+x1:
                    patterns.append(pat)
                    if dimension=='category':
                        profile_map[cid]['patterns'].append(pat)
                        if eligible and status in ['Newly observed','No longer observed','Buying more often','Buying less often']:
                            profile_map[cid]['changes'] += 1
                if eligible: per.append(pat)
            if not per: continue
            frame = pd.DataFrame(per)
            diff = frame.change.to_numpy()
            up,down = int((diff>1e-10).sum()),int((diff < -1e-10).sum())
            seed=int(hashlib.sha256(f'{dimension}:{entity}'.encode()).hexdigest()[:8],16)
            rng=np.random.default_rng(seed)
            # Bounded batching avoids an unbounded bootstrap allocation on larger uploads.
            means=np.concatenate([rng.choice(diff,size=(50,len(diff)),replace=True).mean(1) for _ in range(20)])
            lo,hi=np.quantile(means,[.025,.975])
            stable=frame[frame.stable_retailer]
            monthly=[]
            for month,g in known.groupby(known.date.dt.to_period('M')):
                monthly.append(dict(month=str(month),rate=float(presence.loc[g.index,entity].groupby(g.customer).mean().mean()),customers=g.customer.nunique()))
            states=frame.status.value_counts().to_dict()
            category_lines=lines[lines[dimension]==entity]
            products=category_lines.groupby('raw_product_text').transaction_id.nunique().sort_values(ascending=False).head(6)
            repeat_buyers=int(((frame.earlier+frame.recent)>=2).sum())
            buyers=int(((frame.earlier+frame.recent)>0).sum())
            candidates.append(dict(id=f'{dimension}:{entity}',dimension=dimension,entity=entity,name=label(entity),
                customers=len(frame),buyers=buyers,repeat_buyers=repeat_buyers,earlier=float(frame.earlier_rate.mean()),recent=float(frame.recent_rate.mean()),
                change=float(diff.mean()),low=float(lo),high=float(hi),
                p=float(binomtest(up,up+down).pvalue) if up+down else 1.,up=up,down=down,unchanged=len(diff)-up-down,
                states=states,score=float(frame.score.mean()),stable_retailer_customers=len(stable),
                stable_retailer_change=float(stable.change.mean()) if len(stable) else None,
                item_share_change=float(frame.item_share_change.mean()),monthly=monthly,
                adjacent=entity in set(focal[dimension]), products=[dict(name=str(k),receipts=int(v)) for k,v in products.items()],
                customer_ids=[p['customer'] for p in per if p['earlier']+p['recent']>0]))
        if candidates:
            qs=benjamini_hochberg(np.array([c['p'] for c in candidates]))
            for c,q in zip(candidates,qs):
                c['q']=float(q)
                enough=c['customers']>=20 and c['buyers']>=10
                direction=c['change']>0
                consistent=(c['up']>c['down']) == direction
                supported=enough and q<.05 and (c['low']>0 or c['high']<0) and consistent
                c['signal']='supported' if supported else 'watch' if abs(c['change'])>=.03 and enough else 'routine'
                c['confidence']='Supported change' if supported else 'Worth watching' if c['signal']=='watch' else 'Descriptive pattern'
                c['headline']=f"{c['name']} is appearing {'more' if direction else 'less'} often" if c['signal']!='routine' else f"{c['name']}: {c['repeat_buyers']} customers bought repeatedly"
                c['conclusion']=f"Across the same {c['customers']} customers, this appears on about {round(c['earlier']*100)} of every 100 shopping trips earlier, compared with {round(c['recent']*100)} recently."
                c['action']=('Check whether retailer availability or smaller baskets explain the decline before exploring retention.' if not direction else 'Check persistence and availability before testing complementary product offers.') if supported else 'Use repeat buyers for follow-up research; collect more receipts before treating this as a lasting change.'
                c['cautions']=[]
                if not enough: c['cautions'].append('Too few comparable customers or category buyers to make a population trend decision.')
                if len(rec.date.dt.to_period('M').unique())<24: c['cautions'].append('Seasonality remains unresolved: there is less than two years of history.')
                if c['change']*c['item_share_change']<0: c['cautions'].append('The share of basket items moves the other way. Changing basket size may explain the headline.')
                if c['stable_retailer_customers']<20: c['cautions'].append('Too few customers with unchanged retailer coverage to check retailer sensitivity reliably.')
                elif c['stable_retailer_change']*c['change']<0: c['cautions'].append('Customers with unchanged retailer coverage move the other way. Treat the aggregate change cautiously.')
                c['rank']=(3 if supported else 2 if c['signal']=='watch' else 1)*100+min(c['buyers'],100)/10+abs(c['change'])*100
                insights.append(c)
    insights.sort(key=lambda c:-c['rank'])
    for p in profiles:
        p['patterns'].sort(key=lambda z:(z['status']=='Not enough history',-abs(z['change']),-z['recent']))
    # Within-category changes in most purchased brand: descriptive, not proven substitution.
    brand_shifts=[]
    branded=lines.dropna(subset=['customer_id','brand']).copy()
    branded['period']=np.where(branded.timestamp<=cut,'earlier','recent')
    counts=branded.drop_duplicates(['transaction_id','category','brand']).groupby(['customer_id','category','period','brand']).size()
    for (cid,cat), group in counts.groupby(level=[0,1]):
        if str(cid) not in group_info or not group_info[str(cid)][3]: continue
        tops={}
        for period in ['earlier','recent']:
            v=group[group.index.get_level_values('period')==period]
            if len(v) and v.max()>=2 and int((v==v.max()).sum())==1: tops[period]=(v.idxmax()[-1],int(v.max()))
        if len(tops)==2 and tops['earlier'][0]!=tops['recent'][0]:
            brand_shifts.append(dict(customer=str(cid),category=label(cat),earlier=tops['earlier'][0],recent=tops['recent'][0],earlier_receipts=tops['earlier'][1],recent_receipts=tops['recent'][1]))
    return dict(sources=sources,synthetic=synthetic,period=dict(start=rec.date.min().isoformat(),end=rec.date.max().isoformat(),split=cut.isoformat()),
        totals=dict(lines=len(lines),receipts=len(rec),customers=len(profiles),comparable=eligible_count,
                    categories=len(set(lines.category.dropna())-{'unclassified'}),functions=len(set(lines.function.dropna())-{'unclassified'}),
                    unknown_customer_receipts=int(rec.customer.isna().sum()),unclassified_lines=int(lines.category.fillna('unclassified').eq('unclassified').sum()),
                    supported=sum(i['signal']=='supported' for i in insights if i['dimension']=='category')),
        customers=profiles,insights=insights,patterns=patterns,receipts=records,brand_shifts=brand_shifts,audit=pl.audit,
        exclusions=dict(insufficient_history=len(profiles)-eligible_count),
        method=dict(individual='At least three receipts in each period. Newly/no longer observed requires two purchases in one period and none in the other. Frequency shifts require a 25-point change and three purchases supporting the direction.',
                    population='Same customers, equal customer weights. At least 20 comparable customers and 10 buyers; paired sign test with Benjamini–Hochberg correction within each view; customer bootstrap interval must exclude zero and agree in direction.',
                    score='Receipt quality × balanced period coverage (full at five receipts per period) × duration (full at 90 days). This rates observation strength, not the probability of intent.',
                    limitations='Absence means not seen in these receipts. It does not prove churn, adoption, substitution or unmet demand. Price, promotions, retailer assortment and seasonality are not causally controlled.'))
