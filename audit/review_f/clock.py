"""Independent clock map: HistData vs Dukascopy at minute resolution. No audit code imported."""
import numpy as np, pandas as pd, json, zoneinfo, datetime as dt
h=pd.read_csv("@GANN_ROOT@/research/data/xauusd_m1_histdata.csv",usecols=['time','close'])
ht=h.time.values.astype(np.int64); hc=h.close.values
print('hist rows',len(ht),'mono viol',(np.diff(ht)<=0).sum(),'range',pd.to_datetime([ht.min(),ht.max()],unit='s').tolist(),'sec%60 nonzero',(ht%60!=0).sum())
o=np.argsort(ht,kind='stable'); ht=ht[o];hc=hc[o]
z=np.load("@LBO_ROOT@/data/m1/XAUUSD.npz")
dt_=z['t'].astype(np.int64)*60; dc=z['c']
print('duka',len(dt_),pd.to_datetime([dt_.min(),dt_.max()],unit='s').tolist())
# put both on dense per-minute log-return dicts by day; test lags in minutes
LAGS=[-120,-61,-60,-59,-2,-1,0,1,2,59,60,61,62,119,120,121,180]
ds=np.arange(int(max(ht[0],dt_[0])//86400),int(min(ht[-1],dt_[-1])//86400)+1)
ds=ds[(ds+3)%7!=5]
rows=[]
hmin=ht//60; dmin=dt_//60
for d in ds:
    i,j=np.searchsorted(dmin,[d*1440,(d+1)*1440])
    if j-i<300: continue
    bm,bc=dmin[i:j],dc[i:j]
    res={}
    for L in LAGS:
        tgt=bm+L
        k=np.searchsorted(hmin,tgt); k[k>=len(hmin)]=len(hmin)-1
        ok=hmin[k]==tgt
        if ok.sum()<200: continue
        idx=np.where(ok)[0]; cons=np.diff(idx)==1
        if cons.sum()<100: continue
        x=np.diff(np.log(hc[k[idx]]))[cons]; y=np.diff(np.log(bc[idx]))[cons]
        if x.std()==0 or y.std()==0: continue
        res[L]=float(np.corrcoef(x,y)[0,1])
    if not res: continue
    best=max(res,key=res.get); second=sorted(res.values())[-2] if len(res)>1 else np.nan
    rows.append((d,best,res[best],second,res.get(0,np.nan),res.get(60,np.nan)))
a=pd.DataFrame(rows,columns=['day','lag','corr','second','c0','c60'])
a['date']=pd.to_datetime(a.day*86400,unit='s')
a.to_pickle('review_f/clock_days.pkl')
print('days',len(a),'lag counts',a.lag.value_counts().to_dict())
print('corr quantiles',a['corr'].quantile([0,.01,.05,.5]).round(3).to_dict(),'low<.5',(a['corr']<.5).sum())
# rule test using tz database rather than audit bounds
NY=zoneinfo.ZoneInfo('America/New_York'); LON=zoneinfo.ZoneInfo('Europe/London')
def rule(d,boundary=2019):
    x=dt.datetime(1970,1,1,tzinfo=dt.timezone.utc)+dt.timedelta(days=int(d),hours=12)
    if x.year<boundary: return 60 if x.astimezone(NY).dst() else 0
    return 60 if x.astimezone(LON).dst() else 0
a['rule']=[rule(d) for d in a.day]
a['us']=[60 if (dt.datetime(1970,1,1,tzinfo=dt.timezone.utc)+dt.timedelta(days=int(d),hours=12)).astimezone(NY).dst() else 0 for d in a.day]
a['eu']=[60 if (dt.datetime(1970,1,1,tzinfo=dt.timezone.utc)+dt.timedelta(days=int(d),hours=12)).astimezone(LON).dst() else 0 for d in a.day]
bad=a[a.lag!=a.rule]
print('rule mismatches',len(bad)); print(bad[['date','lag','corr','second','c0','c60','rule']].to_string()[:3000])
# days on which US and EU disagree: the only ones that identify the regime
dis=a[a.us!=a.eu]
print('disagree days',len(dis),'by year: matches US / matches EU'); 
print(dis.assign(y=dis.date.dt.year,mU=dis.lag==dis.us,mE=dis.lag==dis.eu).groupby('y')[['mU','mE']].sum().T.to_string())
print(dis[(dis.date>='2018-02-01')&(dis.date<='2019-04-15')][['date','lag','us','eu','corr']].to_string())
# segments
seg=[];s=0;L=a.lag.values
for i in range(1,len(a)+1):
    if i==len(a) or L[i]!=L[s]: seg.append((str(a.date.iloc[s].date()),str(a.date.iloc[i-1].date()),int(L[s]),i-s)); s=i
print('segments',len(seg)); print(seg[:6],seg[-4:])
a.to_pickle('review_f/clock_days.pkl')
# margin at the two main lags
print('second-best corr quantiles',a.second.quantile([.5,.99,1]).round(3).to_dict())
