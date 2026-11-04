"""Own EDGE-1-F6 and SW-1 checks. Own code."""
import numpy as np,pandas as pd,math,json,itertools
exec(open('review_f/_common.py').read())
C="BTC ETH BNB XRP ADA SOL DOGE LTC LINK DOT AVAX TRX".split()
P={}
for c in C:
    z=np.load(f"{D2}/C_{c}_D1.npz");s=pd.Series(z['c'].astype(float),index=pd.to_datetime(z['t'],unit='s'));P[c]=s[~s.index.duplicated(keep='last')]
X=pd.DataFrame(P).sort_index()
print(X.index[0],X.index[-1],X.notna().sum().to_dict())
sh=lambda s:s.mean()/s.std()*365**.5
def f6(X,n=50,lag=1,cost=.001,sigma=True,vt=.02):
    r=X.pct_change(fill_method=None);vol=r.rolling(60).std();ma=X.rolling(n).mean()
    sig=(X>ma).astype(float).where(ma.notna())
    w=(sig*(vt/vol)).clip(upper=1.0);k=w.notna().sum(axis=1).replace(0,np.nan);w=w.div(k,axis=0)
    pos=w.shift(lag);o=(pos*r).sum(axis=1)-pos.diff().abs().sum(axis=1)*cost
    return o[pos.notna().any(axis=1)]
s=f6(X);print('F6 days',len(s),'Sharpe',round(sh(s),3),'DSR ledger',round(dsr(s.values,178991)[0],4),'114500',round(dsr(s.values,114500)[0],4),'SR daily',round(s.mean()/s.std(),4),'t',round(s.mean()/s.std()*len(s)**.5,2))
for lag in (1,2,3): 
    q=f6(X,lag=lag);print('lag',lag,'Sharpe',round(sh(q),3),'DSR178991',round(dsr(q.values,178991)[0],3))
q=f6(X);
print('by half',round(sh(s[s.index<'2022-07-01']),3),round(sh(s[s.index>='2022-07-01']),3))
print('last 3y',round(sh(s[s.index>='2023-10-01']),3),'since 2024',round(sh(s[s.index>='2024-01-01']),3),'2025+',round(sh(s[s.index>='2025-01-01']),3))
# excess vs BH? beta
bh=(X.pct_change(fill_method=None)).mean(axis=1).reindex(s.index)
b=np.cov(s,bh)[0,1]/bh.var();res=s-b*bh
print('corr to equal wt coin mkt',round(np.corrcoef(s,bh)[0,1],3),'beta',round(b,3),'alpha ann',round(res.mean()*365,3),'alpha t',round(res.mean()/res.std()*len(res)**.5,2))
# pre-listing coverage: how many coins live in first year
print('coins with ma ready by year-end',{y:int(X[X.index.year==y].notna().iloc[-1].sum()) for y in range(2017,2027)})
# PBO null baseline for N variants with audit's rule lam<=0
for N in (5,10,12):
    print('PBO if ranks uniform N',N,sum(1 for k in range(1,N+1) if k/(N+1)<=.5)/N)
# F6 variants: are all strongly positive?
vs={n:f6(X,n=n) for n in (20,30,50,100,200)}
print({n:round(sh(v),2) for n,v in vs.items()})
# SW-1
m=load('US500')
z=np.load(DD+"/US500_D1.npz");pos=z['sp'][z['sp']>0];sp=1.5*float(np.median(pos));
def ibs(m,sp,delay=0):
    c,o,h,l,t=m['c'],m['o'],m['h'],m['l'],m['t'];x=np.where(h>l,(c-l)/np.where(h>l,h-l,1),np.nan);n=len(c);i=252;out=[]
    while i<n-2-delay:
        if x[i]<.2:
            j=i+1
            while j<n-2 and j-i<15 and not(x[j]>.8 or c[j]>h[j-1]): j+=1
            a,b=i+1+delay,j+1+delay
            if b>=n: break
            nt=int(t[b]//86400-t[a]//86400)
            out.append(dict(sig=t[i],ret=o[b]/o[a]-1-sp/o[a]-nt*.05/365));i=j+1
        else: i+=1
    return pd.DataFrame(out)
t=ibs(m,sp);r=t.ret.values;h=len(r)//2
print('SW-1 n',len(r),'PF',round(PF(r),3),round(PF(r[:h]),3),round(PF(r[h:]),3),'DSR10',round(dsr(r,10)[0],3),'50',round(dsr(r,50)[0],3),'114500',round(dsr(r,114500)[0],3),'178991',round(dsr(r,178991)[0],3),'delay1 PF',round(PF(ibs(m,sp,1).ret.values),3))
y=pd.to_datetime(t.sig,unit='s').dt.year;g=t.groupby(y).ret.sum();print('SW years neg',(g<0).sum(),'of',len(g))
g20=t[y!=2020].ret.values;print('SW ex-2020 PF',round(PF(g20),3),'n',len(g20),'t',round(g20.mean()/g20.std()*len(g20)**.5,2),'DSR178991',round(dsr(g20,178991)[0],3))
# US500 gap
T=pd.to_datetime(m['t'],unit='s');d=np.diff(m['t'])/86400;print('US500 gaps>4d',[(str(T[i])[:10],str(T[i+1])[:10],d[i]) for i in np.flatnonzero(d>4)])
print('rows per year',pd.Series(T.year).value_counts().sort_index().to_dict())
