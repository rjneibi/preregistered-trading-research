"""TUNE-1 HOLD-M pooled outlier check and DSR on independent trades."""
import numpy as np,pandas as pd,math,os
from scipy.stats import norm,skew,kurtosis
exec(open('review_f/_common.py').read())
syms="DE40 FRA40 ESP35 AUS200 HK50 EWG EWJ EWU EFA EEM FXI INDA SMH XLK XLV XLP XLE VNQ".split()
allt=[]
for s in syms:
    m=load(s); t=a1(m); t['sym']=s; allt.append(t)
    print(s,len(m['c']),str(pd.to_datetime(m['t'][0],unit='s'))[:10],str(pd.to_datetime(m['t'][-1],unit='s'))[:10],'n',len(t),'PF %.2f'%PF(t.ret.values),'sp %.4f'%m['sp'],'max|d1|%.3f'%np.abs(np.diff(np.log(m['c']))).max())
T=pd.concat(allt).reset_index(drop=True); r=T.ret.values
print('pooled n',len(r),'PF',round(PF(r),3),'mean',r.mean(),'std',r.std(ddof=1),'SR',r.mean()/r.std(ddof=1),'skew',skew(r),'kurt',kurtosis(r,fisher=False))
print(T.reindex(T.ret.abs().sort_values(ascending=False).index)[['sym','sig','ret','hold']].assign(d=lambda x:pd.to_datetime(x.sig,unit='s')).head(10).to_string())
for N in (9,2000,114500,178991): print(N,dsr(r,N))
b=T[T.ret.abs()<.5].ret.values
print('dropping |ret|>50%: n',len(b),'PF',round(PF(b),3),'SR',b.mean()/b.std(ddof=1),[ (N,round(dsr(b,N)[0],4)) for N in (9,2000,178991)])
# clusters: trades per signal week, effective T
w=(T.sig//(7*86400)); print('distinct signal weeks',w.nunique())
g=T.groupby(w).ret.mean().values; print('week-cluster mean SR',g.mean()/g.std(ddof=1),'T',len(g),'t',g.mean()/g.std(ddof=1)*len(g)**.5, [(N,round(dsr(g,N)[0],4)) for N in (9,2000,178991)])
# HOLD-T
pool=[]
t0=int(pd.Timestamp('2023-10-13').timestamp())
for s in "US500 US30 US2000 USTEC".split():
    m=load(s); q=a1(m); q=q[q.sig>=t0]; q['sym']=s; pool.append(q)
H=pd.concat(pool).reset_index(drop=True); r=H.ret.values
print('HOLD-T',len(r),round(PF(r),3),'DSR',[(N,round(dsr(r,N)[0],4)) for N in (4760,114500,178991)],'t',r.mean()/r.std(ddof=1)*len(r)**.5)
print(H.groupby('sym').ret.agg(['size','sum']))
print('signal days distinct',H.sig.nunique(),' weeks',(H.sig//(7*86400)).nunique())
g=H.groupby(H.sig//(7*86400)).ret.mean().values
print('week cluster T',len(g),'t',g.mean()/g.std(ddof=1)*len(g)**.5,[(N,round(dsr(g,N)[0],4)) for N in (4760,178991)])
c=np.corrcoef([H[H.sym==s].ret.sum() for s in ['US500']]) 
# trades in HOLD-T window contaminated: overlap with XM-1 sample
xm=H[H.sym.isin(['US500'])]; print('US500 HOLD-T trades',len(xm))
print('=== splits ===')
ETF="EWG EWJ EWU EFA EEM FXI INDA SMH XLK XLV XLP XLE VNQ".split()
def adjust(m,thr=.3):
    c,o,h,l=[m[k].copy() for k in 'cohl']
    rat=o[1:]/c[:-1]   # overnight jump
    ev=[]
    for i in np.flatnonzero((rat>1.45)|(rat<.68)):
        k=rat[i]; ev.append((str(pd.to_datetime(m['t'][i+1],unit='s'))[:10],round(c[i],2),round(o[i+1],2),round(float(k),3)))
        for a in (c,o,h,l): a[:i+1]*=k
    return dict(m,c=c,o=o,h=h,l=l),ev
adjt=[]
for s in syms:
    m=load(s); ma,ev=adjust(m) if s in ETF else (m,[])
    if ev: print(s,ev)
    t=a1(dict(ma,sp=m['sp'])); t['sym']=s; adjt.append(t)
    # note: sp constant in today-dollars, kept
A=pd.concat(adjt).reset_index(drop=True); r=A.ret.values
per=A.groupby('sym').ret.apply(lambda x:PF(x.values))
print('ADJUSTED pooled n',len(r),'PF',round(PF(r),3),'skew',round(float(skew(r)),2),'kurt',round(float(kurtosis(r,fisher=False)),1),'SR',round(r.mean()/r.std(ddof=1),4),'avg bp',round(r.mean()*1e4,1))
print('share PF>1',(per>1).mean()); print(per.round(2).to_dict())
print('DSR adj',[(N,round(dsr(r,N)[0],4)) for N in (9,2000,4760,114500,178991)])
print('top5 adj',np.sort(r)[-5:].round(3),np.sort(r)[:5].round(3))
print('ETF only unadjusted PF',round(PF(T[T.sym.isin(ETF)].ret.values),3),'adjusted',round(PF(A[A.sym.isin(ETF)].ret.values),3))
