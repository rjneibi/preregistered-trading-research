"""Independent XM-1-A1 re-derivation. No audit or original code imported."""
import numpy as np, pandas as pd, math, json
from scipy.stats import norm, skew, kurtosis
z=np.load("@GANN_ROOT@/research/cross_market/data/US500_D1.npz")
print({k:(z[k].shape,z[k].dtype) for k in z.files}, 'sp raw', z['sp'] if z['sp'].ndim==0 else (np.unique(z['sp'])[:8], np.median(z['sp'])))
df=pd.DataFrame({k:z[k].astype(float) for k in 'ohlc'}); df['t']=z['t'].astype(np.int64)
print('rows',len(df),'dupe stamps',df.t.duplicated().sum(),'nonmono',(df.t.diff()<=0).sum())
print(pd.to_datetime(df.t,unit='s').iloc[[0,1,-2,-1]].tolist())
print('weekday counts',pd.to_datetime(df.t,unit='s').dt.dayofweek.value_counts().sort_index().to_dict())
print('stamp hour',pd.to_datetime(df.t,unit='s').dt.hour.value_counts().to_dict())
df=df.drop_duplicates('t',keep='last').sort_values('t').reset_index(drop=True)
gap=(df.t.diff()/86400)
print('rows after dedupe',len(df),'max gap days',gap.max(),'gaps>5',(gap>5).sum())
sp0=z['sp']; pos=sp0[sp0>0] if sp0.ndim else np.array([float(sp0)])
SP=1.5*float(np.median(pos)) if len(pos) else 0.
print('spread used',SP,'pos spread share',len(pos)/max(sp0.size,1))
c=df.c.values;o=df.o.values;t=df.t.values
def rsi_wilder(c,n=2):
    d=np.diff(c,prepend=np.nan); up=np.nan_to_num(np.clip(d,0,None)); dn=np.nan_to_num(np.clip(-d,0,None))
    a=1/n; u=v=0.; out=np.full(len(c),np.nan)
    u=up[1:n+1].mean(); v=dn[1:n+1].mean()
    for i in range(n,len(c)):
        if i>n: u=u*(1-a)+up[i]*a; v=v*(1-a)+dn[i]*a
        out[i]=100 if v==0 else 100-100/(1+u/v)
    return out
def rsi_adj(c):
    s=pd.Series(c).diff(); u=s.clip(lower=0).ewm(alpha=.5).mean(); v=(-s.clip(upper=0)).ewm(alpha=.5).mean()
    return (100-100/(1+u/v)).values
sma=lambda x,n: pd.Series(x).rolling(n).mean().values
def trades(rsi,sp=SP,fin=.05/365,delay=0,fillopen=True,thr=10,start=200):
    s200,s5=sma(c,200),sma(c,5); out=[];i=start;n=len(c)
    while i<n-1-delay-1:
        if rsi[i]<thr and c[i]>s200[i]:
            j=i+1
            while j<n-2 and j-i<10 and not c[j]>s5[j]: j+=1
            a=i+1+delay; b=j+1+delay
            if b>=n: break
            pa,pb=(o[a],o[b]) if fillopen else (c[i],c[j])
            nights=int(t[b]//86400-t[a]//86400)
            out.append(dict(sig=t[i],ret=pb/pa-1-sp/pa-nights*fin,hold=j-i,gross=pb/pa-1,a=a,b=b)); i=j+1
        else: i+=1
    return pd.DataFrame(out)
def PF(r): return r[r>0].sum()/-r[r<0].sum()
def dsr(r,N):
    r=np.asarray(r);T=len(r);sr=r.mean()/r.std(ddof=1);g=0.5772156649;v=1/T
    sr0=v**.5*((1-g)*norm.ppf(1-1/N)+g*norm.ppf(1-1/(N*math.e)))
    d=1-skew(r)*sr+(kurtosis(r,fisher=False)-1)/4*sr*sr
    return norm.cdf((sr-sr0)*math.sqrt(T-1)/math.sqrt(d)),sr,sr0
out={}
for nm,rs in (('adjusted ewm RSI(alpha .5)',rsi_adj(c)),('Wilder RSI seeded SMA',rsi_wilder(c))):
    for fo in (True,False):
        tr=trades(rs,fillopen=fo); r=tr.ret.values;h=len(r)//2
        print(nm,'open' if fo else 'close','n',len(r),'PF %.3f  halves %.3f %.3f win %.3f'%(PF(r),PF(r[:h]),PF(r[h:]),(r>0).mean()),'DSR12 %.3f DSR17 %.3f DSR114500 %.3f DSR178991 %.3f'%(dsr(r,12)[0],dsr(r,17)[0],dsr(r,114500)[0],dsr(r,178991)[0]),'SR %.4f t %.2f'%(dsr(r,12)[1],dsr(r,12)[1]*len(r)**.5))
tr=trades(rsi_adj(c)); r=tr.ret.values
y=pd.to_datetime(tr.sig,unit='s').dt.year
g=tr.groupby(y).ret.sum()
print('years',len(g),'neg',(g<0).sum(),g.round(3).to_dict())
print('years 2018+ neg',(g[g.index>=2018]<0).sum(),'of',(g.index>=2018).sum())
print('nospread',PF(trades(rsi_adj(c),sp=0).ret.values),'nofin',PF(trades(rsi_adj(c),fin=0).ret.values),'gross',PF(tr.gross.values))
for d in (1,2): 
    q=trades(rsi_adj(c),delay=d).ret.values; print('delay',d,'n',len(q),'PF',round(PF(q),3))
# daily-return Sharpe and DD vs B&H over same window, cash at 0
dates=df.t.values
start=200
ret=np.zeros(len(c));
for _,x in tr.iterrows():
    a,b=int(x.a),int(x.b)
    ret[a:b]=o[a+1:b+1]/o[a:b]-1
    ret[a]-=SP/o[a]
s=ret[start:]; bh=(o[1:]/o[:-1]-1)[start:]
sh=lambda x:x.mean()/x.std()*252**.5
dd=lambda x:((1+x).cumprod()/np.maximum.accumulate((1+x).cumprod())-1).min()
print('daily Sharpe rule %.2f bh %.2f maxDD rule %.3f bh %.3f expo %.3f'%(sh(s),sh(bh),dd(s),dd(bh),(ret[start:]!=0).mean()))
