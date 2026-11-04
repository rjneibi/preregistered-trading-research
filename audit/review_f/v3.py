"""Independent FINAL_v3 on true-UTC bars. Own clock rule from tz database. No audit/original code imported."""
import numpy as np, pandas as pd, zoneinfo, datetime as dt, sys
d=pd.read_csv("@GANN_ROOT@/research/data/xauusd_m1_histdata.csv")
s=d.time.values.astype(np.int64)
ts=pd.to_datetime(s,unit='s',utc=True)
# rule: through 2018 stamp-UTC=+1h while New York on DST; from 2019 while London on DST. evaluate on the stamp minus 1h is unneeded as markets closed at switches.
ny=(ts.tz_convert('America/New_York').map(lambda x:x.dst()!=dt.timedelta(0))) if False else None
def dstflag(ts,tz):
    # fast: offset minus standard offset
    loc=ts.tz_convert(tz)
    off=(loc.tz_localize(None)-ts.tz_localize(None))
    return off
offny=dstflag(ts,'America/New_York'); offln=dstflag(ts,'Europe/London')
us=(offny==pd.Timedelta(hours=-4)); eu=(offln==pd.Timedelta(hours=1))
yr=ts.year.values
sh=np.where(yr<2019,us,eu)
print('share of bars shifted all',sh.mean(),'2013+',sh[yr>=2013].mean(), '2015-06+',sh[ts>=pd.Timestamp('2015-06-19',tz='UTC')].mean())
t2=s-sh.astype(np.int64)*3600
m=pd.DataFrame({'o':d.open.values,'h':d.high.values,'l':d.low.values,'c':d.close.values},index=pd.to_datetime(t2,unit='s',utc=True))
print('dupes after shift',m.index.duplicated().sum(),'mono',m.index.is_monotonic_increasing)
m=m[~m.index.duplicated()].sort_index()
def rs(x,r):
    g=x.resample(r,label='left',closed='left')
    a=pd.DataFrame(dict(o=g.o.first(),h=g.h.max(),l=g.l.min(),c=g.c.last())); return a.dropna()
def wilder(h,n=14):
    pc=h.c.shift(1); tr=np.maximum.reduce([(h.h-h.l).values,(h.h-pc).abs().values,(h.l-pc).abs().values])
    a=np.full(len(h),np.nan); a[n]=np.nanmean(tr[1:n+1])
    for i in range(n+1,len(h)): a[i]=(a[i-1]*(n-1)+tr[i])/n
    return pd.Series(a,index=h.index)
def run(start,end,variant='v3',fill_gap=False):
    x=m[(m.index>=start-pd.Timedelta(days=60))&(m.index<=end)]
    h1=rs(x,'1h');h4=rs(x,'4h');d1=rs(x,'1D');atr=wilder(h1)
    T=x.index.values;O=x.o.values;H=x.h.values;L=x.l.values;C=x.c.values
    days=d1.index[(d1.index>=start)&(d1.index<=end)]
    out=[]
    for dy in days:
        p=d1.index.get_loc(dy)
        if p<1: continue
        pr=d1.iloc[p-1]; op=d1.o.iloc[p]
        cl=h4[h4.index+pd.Timedelta(hours=4)<=dy]
        if len(cl)<50: continue
        pa=atr[atr.index<=dy-pd.Timedelta(hours=1)]
        if not len(pa) or not np.isfinite(pa.iloc[-1]): continue
        a=float(pa.iloc[-1])
        pp=(pr.h+pr.l+pr.c)/3; rng=pr.h-pr.l
        R3=round(pp+rng,2);S3=round(pp-rng,2)
        base=cl.c.tail(10).values
        live=[]
        if abs(R3-op)<=10*a and not (base>R3).any(): live.append(('BUY',R3))
        if abs(S3-op)<=10*a and not (base<S3).any(): live.append(('SELL',S3))
        if not live: continue
        taken=False
        for ot,r in h4[(h4.index>=dy)&(h4.index<dy+pd.Timedelta(days=1))].iterrows():
            cur=ot+pd.Timedelta(hours=4)
            if cur>end: break
            hit=[z for z in live if (z[0]=='BUY' and r.c>z[1]) or (z[0]=='SELL' and r.c<z[1])]
            live=[z for z in live if z not in hit]
            if not hit: continue
            for side,lv in hit:
                if cur.hour not in (12,16,20) or cur.dayofweek==0: continue
                k=(cur.date())
                if out and out[-1]['day']==k: continue
                sg=1 if side=='BUY' else -1
                i0=np.searchsorted(T,np.datetime64(cur.tz_localize(None)))
                if i0>=len(T): continue
                f=O[i0];tp=f+sg*1.4*a;sl=f-sg*2.1*a
                iend=min(max(np.searchsorted(T,T[i0]+np.timedelta64(120,'h')),i0+1),len(T))
                its=np.searchsorted(T,T[i0]+np.timedelta64(24,'h'))
                pnl=None
                for i in range(i0,iend):
                    if (L[i]<=sl if sg>0 else H[i]>=sl): pnl=sg*(sl-f);why='sl';break
                    if (H[i]>=tp if sg>0 else L[i]<=tp): pnl=sg*(tp-f);why='tp';break
                    if i>=its: pnl=sg*(C[i]-f);why='ts';break
                if pnl is None: pnl=sg*(C[iend-1]-f);why='end'
                out.append(dict(ts=cur,day=k,side=side,pnl=pnl*100-20,why=why,gross=pnl*100,level=lv,atr=a))
    return pd.DataFrame(out)
A=run(pd.Timestamp('2015-06-19',tz='UTC'),pd.Timestamp('2021-06-18 23:59',tz='UTC'))
B=run(pd.Timestamp('2021-06-19',tz='UTC'),pd.Timestamp('2026-06-19 17:57',tz='UTC'))
def S(t):
    p=t.pnl.values;w=p[p>0].sum();l=-p[p<0].sum();c=np.cumsum(p)
    return dict(n=len(p),pf=round(w/l,3),net=round(p.sum()),wr=round((p>0).mean(),3),dd=round((np.maximum.accumulate(c)-c).max()))
print('old',S(A));print('new',S(B));T=pd.concat([A,B]).sort_values('ts');print('pooled',S(T))
T.to_csv('review_f/v3_mine.csv',index=False)
st=pd.read_csv('phaseC/fable_v3_true.csv',parse_dates=['ts'])
st['k']=st.ts.astype(str).str[:19]+st.dir; T['k']=T.ts.astype(str).str[:19]+T.side
mg=st.merge(T,on='k',how='outer',indicator=True,suffixes=('_a','_m'))
print(mg._merge.value_counts().to_dict())
b=mg[mg._merge=='both']; dif=(b.pnl_a-b.pnl_m).abs()
print('within $1',(dif<1).sum(),'of',len(b),'max',dif.max())
print(b[dif>=1][['k','pnl_a','pnl_m','why']].head(12).to_string())
print(mg[mg._merge!='both'][['k','pnl_a','pnl_m','_merge']].head(20).to_string())
