"""H3 gate 1 sensitivity, own OU fit. Uses silver bid M1 built by the audit (sandbox file) and own true-UTC gold."""
import numpy as np,pandas as pd
z=np.load('_copy/data/xag_m1_ticks.parquet.npz')
s=pd.DataFrame({k:z[k] for k in 'oc'},index=pd.to_datetime(z['t']*60,unit='s',utc=True))
print('silver m1',len(s),s.index[0],s.index[-1],'px range',s.c.min(),s.c.max())
print('silver M1 |ret|>2%:',(np.abs(np.diff(np.log(s.c.values)))>.02).sum())
d=pd.read_csv("@GANN_ROOT@/research/data/xauusd_m1_histdata.csv",usecols=['time','close'])
ts=pd.to_datetime(d.time.values,unit='s',utc=True)
us=(ts.tz_convert('America/New_York').tz_localize(None)-ts.tz_localize(None))==pd.Timedelta(hours=-4)
eu=(ts.tz_convert('Europe/London').tz_localize(None)-ts.tz_localize(None))==pd.Timedelta(hours=1)
sh=np.where(ts.year<2019,us,eu)
g=pd.Series(d.close.values,index=ts-pd.to_timedelta(sh.astype(int),unit='h'))
gh=g.resample('1h').last().dropna(); sh1=s.c.resample('1h').last().dropna()
df=pd.DataFrame({'x':gh,'g':sh1}).dropna(); lx,lg=np.log(df.x),np.log(df.g)
months=sorted(set(lx.index.to_period('M').astype(str)));B={}
for mo in months:
    t0=pd.Timestamp(mo+'-01',tz='UTC');w=(lx.index<t0)&(lx.index>=t0-pd.Timedelta(days=90))
    if w.sum()<500: continue
    x,y=lg[w].values,lx[w].values;B[mo]=np.cov(x,y,bias=True)[0,1]/np.var(x)
print('betas n',len(B),'min',min(B.items(),key=lambda k:k[1]),'max',max(B.items(),key=lambda k:k[1]),'share<.3',np.mean(np.array(list(B.values()))<.3))
print({k:round(v,2) for k,v in list(B.items())[:8]})
keep=lx.index.to_period('M').astype(str).isin(list(B));lx,lg=lx[keep],lg[keep]
b=lx.index.to_period('M').astype(str).map(B).values.astype(float)
sp=lx.values-b*lg.values;cut=int(len(sp)*.7)
def fit(x):
    a,c=np.polyfit(x[:-1],x[1:],1); e=x[1:]-c-a*x[:-1];n=len(x)
    return a,(-np.log(2)/np.log(a) if 0<a<1 else np.nan),(1-a)/np.sqrt((1-a*a)/n)
print('stitched IS',fit(sp[:cut]),'n',cut)
# remove the month-end level jumps: demean within each month with each month's beta
per=lx.index.to_period('M').astype(str).values[:cut]
S=pd.Series(sp[:cut]); 
jump=np.r_[0,np.diff(sp[:cut])]; ch=per[1:]!=per[:-1]
dj=jump.copy(); dj[1:][ch]=0 # replace the jump at each boundary by zero
print('stitched, month-boundary jumps removed',fit(np.cumsum(dj)))
print('share of IS abs change from boundary jumps',np.abs(jump[1:][ch]).sum()/np.abs(jump).sum(), 'n boundaries',ch.sum(),'mean abs jump',np.abs(jump[1:][ch]).mean(),'mean abs normal',np.abs(jump[1:][~ch]).mean())
# causal: fixed trailing beta from first IS month held through whole IS
print('single-beta (median) whole IS',fit(lx.values[:cut]-np.median(b)*lg.values[:cut]))
# within month half-life, no t gate
hl=[];tv=[]
for mo in pd.unique(per):
    q=per==mo
    if q.sum()>300:
        a,h,t=fit(sp[:cut][q]); hl.append(h); tv.append(t)
hl=np.array(hl);tv=np.array(tv)
print('months',len(hl),'within-month HL: median',np.nanmedian(hl),'share in [4,240]',np.mean((hl>=4)&(hl<=240)),'share t>=3',np.mean(tv>=3),'median t',np.median(tv))
print('t needed: for n=500, t>=3 implies HL<=',-np.log(2)/np.log(1-2*9/500),'; n=1500:',-np.log(2)/np.log(1-2*9/1500),'; n=2160:',-np.log(2)/np.log(1-2*9/2160))
