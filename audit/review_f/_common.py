import numpy as np,pandas as pd,math,os
from scipy.stats import norm,skew,kurtosis
DD="@GANN_ROOT@/research/cross_market/data";D2="@GANN_ROOT@/research/cross_market/data_edge"
def load(s):
    for d in (DD,D2):
        p=f"{d}/{s}_D1.npz"
        if os.path.exists(p):
            z=np.load(p);df=pd.DataFrame({k:z[k].astype(float) for k in 'ohlc'});df['t']=z['t'].astype(np.int64)
            df=df.drop_duplicates('t',keep='last').sort_values('t')
            pos=z['sp'][z['sp']>0];sp=1.5*float(np.median(pos)) if len(pos) else 0.
            sp=max(sp,.0002*float(df.c.median()))
            return dict(t=df.t.values,o=df.o.values,h=df.h.values,l=df.l.values,c=df.c.values,sp=sp)
    raise FileNotFoundError(s)
def rsi2(c):
    s=pd.Series(c).diff();u=s.clip(lower=0).ewm(alpha=.5).mean();v=(-s.clip(upper=0)).ewm(alpha=.5).mean()
    return (100-100/(1+u/v.replace(0,1e-12))).values
def a1(m,thr=10,fin=.05/365,delay=0,spm=1):
    c,o,t=m['c'],m['o'],m['t'];r=rsi2(c);s200=pd.Series(c).rolling(200).mean().values;s5=pd.Series(c).rolling(5).mean().values
    out=[];i=200;n=len(c)
    while i<n-2-delay:
        if r[i]<thr and c[i]>s200[i]:
            j=i+1
            while j<n-2 and j-i<10 and not c[j]>s5[j]: j+=1
            a,b=i+1+delay,j+1+delay
            if b>=n: break
            nt=int(t[b]//86400-t[a]//86400)
            out.append(dict(sig=int(t[i]),ret=o[b]/o[a]-1-spm*m['sp']/o[a]-nt*fin,hold=j-i)); i=j+1
        else: i+=1
    return pd.DataFrame(out)
def PF(r): r=np.asarray(r);return r[r>0].sum()/-r[r<0].sum()
def dsr(r,N):
    r=np.asarray(r);T=len(r);sr=r.mean()/r.std(ddof=1);g=0.5772156649;v=1/T
    sr0=v**.5*((1-g)*norm.ppf(1-1/N)+g*norm.ppf(1-1/(N*math.e)))
    d=1-skew(r)*sr+(kurtosis(r,fisher=False)-1)/4*sr*sr
    return float(norm.cdf((sr-sr0)*math.sqrt(T-1)/math.sqrt(d))),float(sr),float(sr0)
