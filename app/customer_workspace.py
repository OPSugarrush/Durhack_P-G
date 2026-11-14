from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.express as px
from needstate.pipeline import run,process_lines
from needstate.config import load_config
from needstate.ingestion.adapters import to_canonical
from needstate.customer_insights import analyse_customers
ROOT=Path(__file__).resolve().parents[1]

@st.cache_resource(show_spinner='Preparing customer histories…')
def prepare(payload,name,mapping,signature):
    cfg=load_config(ROOT/'configs/pipeline.yaml')
    if payload:
        import io,yaml
        m=yaml.safe_load(mapping) if mapping else cfg.mapping
        raw=pd.read_csv(io.BytesIO(payload)) if name.endswith('.csv') else pd.read_excel(io.BytesIO(payload),sheet_name=m.get('source',{}).get('sheet',0))
        pl=process_lines(to_canonical(raw,m),cfg)
    else: pl=run(str(ROOT/'configs/pipeline.yaml'))
    return pl,analyse_customers(pl.lines,pl.quality)

def main():
    st.set_page_config(page_title='NeedState | Customer intelligence',layout='wide')
    st.markdown('''<style>.block-container{max-width:1280px;padding-top:2.5rem}h1{letter-spacing:-.045em;font-size:2.7rem!important}h2,h3{letter-spacing:-.025em}[data-testid="stMetric"]{background:white;border:1px solid #dde5ed;border-radius:12px;padding:18px}[data-testid="stSidebar"]{background:#e6edf3}</style>''',unsafe_allow_html=True)
    st.sidebar.markdown('## NEEDSTATE\nCustomer intelligence')
    with st.sidebar.expander('Data source'):
        source=st.file_uploader('Receipt data',type=['xlsx','csv'])
        mapping=st.file_uploader('Column mapping',type=['yaml','yml'])
    cfg=load_config(ROOT/'configs/pipeline.yaml')
    signature=tuple((str(p),p.stat().st_mtime_ns) for p in [cfg.input_path,*list((ROOT/'configs').rglob('*.yaml'))] if p.exists())
    try: pl,(customers,d,s,r,x,cut)=prepare(source.getvalue() if source else None,source.name if source else '',mapping.getvalue() if mapping else None,signature)
    except (ValueError,KeyError,OSError) as e: st.error(f'Unable to read this source: {e}'); st.stop()
    st.sidebar.caption(f'{r.date.min():%d %b %Y} — {r.date.max():%d %b %Y}')
    st.sidebar.caption('Synthetic demonstration data' if not source else 'Uploaded data: provenance supplied by you')
    if customers.empty: st.info('Add customer identifiers to connect receipts into histories.'); st.stop()
    def label(v): return v.replace('_',' ').title()
    def overview():
        st.caption('CUSTOMER INSIGHTS'); st.title('Understand what is changing.')
        st.write('Prioritise changes in purchase routines, inspect the customers behind them, and decide what deserves further investigation.')
        a,b,c=st.columns(3)
        a.metric('Customers observed',len(customers)); b.metric('Comparable customer histories',d[d.Eligible].Customer.nunique()); c.metric('Supported category changes',int(s.Decision.eq('Supported directional change').sum()) if len(s) else 0)
        st.caption(f'Earlier versus recent receipts, split on {cut:%d %b %Y}. Each customer has equal weight; comparable histories need at least three receipts in each period.')
        st.subheader('Research priorities')
        if s.empty: st.info('More repeat receipts are needed before reporting population change.'); return
        focus=st.selectbox('Business focus',['All categories','P&G adjacent categories'])
        view=s if focus=='All categories' else s[s.Category.isin(pl.hierarchy.loc[pl.lens.in_portfolio(pl.hierarchy),'category'])]
        for row in view.head(5).itertuples():
            with st.container(border=True):
                left,right=st.columns([4,1]); left.subheader(label(row.Category)); left.write(row.Decision); right.metric('Frequency change',f'{row.Change:+.1f} pp')
                st.write(f'{row.Customers} comparable customers: {row.Increasing} show repeated increases, {row.Decreasing} show repeated decreases, and {row.Routine} maintain an established routine.')
                st.caption(f'95% customer-bootstrap interval: {row.Low:+.1f} to {row.High:+.1f} points. Corrected directional-test q={row.q:.3f}. Average history evidence: {row.Evidence:.0f}/100.')
                st.write('Next investigation: '+('Check persistence in a later period and across retailers before testing a category campaign.' if row.Decision.startswith('Supported') else 'Interview repeat buyers to understand the routine; gather more history before acting on a directional shift.'))
                if st.button('Explore these customers',key=row.Category): st.session_state.focus=row.Category; st.switch_page(cp)
        with st.expander('Compare all categories and export'):
            st.dataframe(view.drop(columns='p'),hide_index=True,width='stretch'); st.download_button('Download evidence',view.to_csv(index=False),'customer_insights.csv','text/csv')
    def explorer():
        st.caption('CUSTOMER EXPLORER'); st.title('Follow the evidence over time.')
        cats=sorted(d.Category.unique()); selected=st.session_state.get('focus',cats[0])
        cat=st.selectbox('Purchase routine',cats,index=cats.index(selected) if selected in cats else 0,format_func=label)
        status=st.selectbox('Behaviour',['All','Increasing','Decreasing','Established routine','Insufficient history'])
        subset=d[d.Category==cat]; subset=subset if status=='All' else subset[subset.Status==status]
        if subset.empty: st.info('No customers match this filter.'); return
        cid=st.selectbox('Customer',subset.sort_values('Evidence',ascending=False).Customer.tolist())
        person=customers.set_index('Customer').loc[cid]; row=subset[subset.Customer==cid].iloc[0]
        a,b,c=st.columns(3); a.metric('Observed receipts',int(person.Receipts)); b.metric('History evidence',f'{person.Evidence}/100'); c.metric('Evidence strength',person.Strength)
        st.caption('Evidence reflects receipt quality, coverage and balanced history. It is not a probability of customer intent.')
        st.subheader(f'{label(cat)} · {row.Status}')
        st.write(f'Purchased on {row.Earlier} of {int(person.Earlier)} earlier receipts and {row.Recent} of {int(person.Recent)} recent receipts: {row.Change:+.1f} percentage points.')
        history=r[r.customer==cid].sort_values('date').copy(); history['Purchase']=x.loc[history.index,cat].astype(int)
        fig=px.scatter(history,x='date',y='Purchase',color='period',hover_data=['quality'],color_discrete_map={'Earlier':'#9aabba','Recent':'#007c83'})
        fig.update_yaxes(tickvals=[0,1],ticktext=['Absent','Purchased']); fig.update_layout(height=260,xaxis_title='Receipt date',yaxis_title=label(cat),legend_title_text='Period',margin=dict(t=10,b=10)); st.plotly_chart(fig,width='stretch')
        st.subheader('Other observed routines'); st.dataframe(d[d.Customer==cid][['Category','Earlier','Recent','Change','Status']],hide_index=True,width='stretch')
        with st.expander('Inspect supporting receipts'):
            tid=st.selectbox('Receipt',history.index.tolist()); st.dataframe(pl.lines[pl.lines.transaction_id==tid][['raw_product_text','category','quantity','line_total']],hide_index=True,width='stretch')
    def evidence():
        st.caption('EVIDENCE & METHOD'); st.title('Know what supports each insight.')
        st.write('Receipts establish purchases. Customer histories establish repetition. Population comparisons follow the same eligible customers across both periods, with equal customer weights.')
        st.subheader('Decision rules')
        st.write('Population changes require a paired sign-test q below 0.05 after correction across categories, plus a customer-bootstrap interval excluding zero. The test measures directional consistency; the interval measures mean purchase-frequency change.')
        st.write('Individual increases/decreases require three receipts per period, at least a 30-point frequency change and three purchases supporting the direction. These are review signals, not statistically confirmed personal predictions.')
        st.write('History evidence = mean receipt quality × balanced coverage (full credit at five receipts per period) × duration (full credit at 90 days). Strong: 80–100; moderate: 50–79; limited: below 50. This is an explicit heuristic, not calibrated confidence.')
        st.warning('Seasonality, retailer assortment, basket size and incomplete observation can explain a change. Six months cannot distinguish seasonal from emerging demand. Synthetic results validate the workflow, not real market demand.')
        st.subheader('Customer coverage'); st.dataframe(customers,hide_index=True,width='stretch')
        with st.expander('Source reconciliation'): st.json(pl.audit)
    cp=st.Page(explorer,title='Explore customers')
    st.navigation([st.Page(overview,title='Customer insights',default=True),cp,st.Page(evidence,title='Evidence & method')]).run()
