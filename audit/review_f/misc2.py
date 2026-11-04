import numpy as np,pandas as pd,json,os
exec(open('review_f/_common.py').read())
m=load('US500');t=a1(dict(m,sp=.45));T=pd.to_datetime(m['t'],unit='s')
s=pd.to_datetime(t.sig,unit='s');print('A1 trades 2025-06..2025-10',t[(s>='2025-06-15')&(s<='2025-10-01')].assign(d=s).to_string())
for sy in ('US30','US2000','USTEC','DE40'):
    q=load(sy);d=np.diff(q['t'])/86400;i=np.flatnonzero(d>6);print(sy,[(str(np.datetime64(int(q['t'][k]),'s'))[:10],d[k]) for k in i])
# F6 and SW-1 DSR at dated ledger N
C="BTC ETH BNB XRP ADA SOL DOGE LTC LINK DOT AVAX TRX".split()
P={}
for c in C:
    z=np.load(f"{D2}/C_{c}_D1.npz");x=pd.Series(z['c'].astype(float),index=pd.to_datetime(z['t'],unit='s'));P[c]=x[~x.index.duplicated(keep='last')]
X=pd.DataFrame(P).sort_index()
def f6(X,cost=None,fund=None,lag=1):
    r=X.pct_change(fill_method=None);v=r.rolling(60).std();ma=X.rolling(50).mean();sig=(X>ma).astype(float).where(ma.notna())
    w=(sig*(.02/v)).clip(upper=1.);k=w.notna().sum(axis=1).replace(0,np.nan);w=w.div(k,axis=0);pos=w.shift(lag)
    c=cost if cost is not None else pd.DataFrame(.001,index=pos.index,columns=pos.columns)
    o=(pos*r).sum(axis=1)-(pos.diff().abs()*c).sum(axis=1)
    if fund is not None: o=o-(pos*fund.reindex(index=pos.index,columns=pos.columns).fillna(0)).sum(axis=1)
    return o[pos.notna().any(axis=1)]
s=f6(X);print('F6 DSR N=625',round(dsr(s.values,625)[0],3))
# perp: spot cost before first funding, per prereg
PUB='_copy/data/public';F={}
X.index=pd.to_datetime(X.index).normalize()
for c in C:
    a=np.array(json.load(open(f'{PUB}/funding_{c}.json')),float);F[c]=pd.Series(a[:,1],index=pd.to_datetime(a[:,0],unit='ms')).resample('D').sum()
F=pd.DataFrame(F);print('first funding',{c:str(F[c].first_valid_index())[:10] for c in C})
slip={c:(.0002 if c in('BTC','ETH') else .001) for c in C}
perp=pd.DataFrame({c:.0005+slip[c] for c in C},index=X.index,columns=C)
perpasrun=f6(X,perp,F)
live=X.index.to_series().apply(lambda d:0)
pre=pd.DataFrame({c:(X.index<F[c].first_valid_index()) for c in C},index=X.index)
fixed=perp.copy()
for c in C: fixed.loc[pre[c],c]=.001+slip[c]
pf=f6(X,fixed,F)
sh=lambda s:s.mean()/s.std()*365**.5
print('perp as run',round(sh(perpasrun),3),'pre-listing coin-days at spot fee as frozen',round(sh(pf),3),'share of coin-days pre-perp',round(float((pre&X.notna()).sum().sum()/X.notna().sum().sum()),3))
# sharpe of BH etc on perp in E5 bh .865 used funding from zero
# US500 SW-1 dated
