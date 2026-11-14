"""Receipt evidence -> customer histories -> paired population insights."""
import numpy as np
import pandas as pd
from scipy.stats import binomtest
from needstate.patterns.stats import benjamini_hochberg

def analyse_customers(lines, quality):
    r=lines.groupby('transaction_id').agg(customer=('customer_id','first'),date=('timestamp','first'))
    r['quality']=quality.data_completeness.reindex(r.index).fillna(0)
    cut=r.date.min()+(r.date.max()-r.date.min())/2
    r['period']=np.where(r.date<=cut,'Earlier','Recent')
    x=pd.crosstab(lines.transaction_id,lines.category).reindex(r.index,fill_value=0).gt(0)
    profiles=[]; details=[]
    for cid,g in r.dropna(subset=['customer']).groupby('customer'):
        a=g.index[g.period=='Earlier']; b=g.index[g.period=='Recent']
        eligible=min(len(a),len(b))>=3
        score=round(100*g.quality.mean()*min(1,min(len(a),len(b))/5)*min(1,(g.date.max()-g.date.min()).days/90))
        profiles.append(dict(Customer=cid,Receipts=len(g),Earlier=len(a),Recent=len(b),Evidence=score,Strength='Strong' if score>=80 else 'Moderate' if score>=50 else 'Limited'))
        for cat in x.columns:
            if cat=='unclassified': continue
            n0=int(x.loc[a,cat].sum()); n1=int(x.loc[b,cat].sum())
            p0=n0/max(1,len(a)); p1=n1/max(1,len(b)); delta=100*(p1-p0)
            state='Insufficient history'
            if eligible:
                state='Established routine' if min(p0,p1)>=.5 else 'No clear shift'
                if abs(delta)>=30 and (n1 if delta>0 else n0)>=3: state='Increasing' if delta>0 else 'Decreasing'
            details.append(dict(Customer=cid,Category=cat,Earlier=n0,Recent=n1,Earlier_rate=p0,Recent_rate=p1,Change=delta,Status=state,Evidence=score,Eligible=eligible))
    profiles=pd.DataFrame(profiles); d=pd.DataFrame(details); rows=[]; rng=np.random.default_rng(42)
    if len(d):
        for cat,g in d[d.Eligible].groupby('Category'):
            delta=g.Change.to_numpy(); up=int((delta>0).sum()); down=int((delta<0).sum())
            lo,hi=np.quantile(rng.choice(delta,(1000,len(delta)),replace=True).mean(1),[.025,.975])
            rows.append(dict(Category=cat,Customers=len(g),Change=delta.mean(),Low=lo,High=hi,Increasing=int((g.Status=='Increasing').sum()),Decreasing=int((g.Status=='Decreasing').sum()),Routine=int((g.Status=='Established routine').sum()),Evidence=g.Evidence.mean(),p=binomtest(up,up+down).pvalue if up+down else 1))
    s=pd.DataFrame(rows)
    if len(s):
        s['q']=benjamini_hochberg(s.p.to_numpy())
        s['Decision']=np.where((s.q<.05)&((s.Low>0)|(s.High<0)),'Supported directional change','Monitor: no clear directional change')
        s=s.sort_values('q')
    return profiles,d,s,r,x,cut
