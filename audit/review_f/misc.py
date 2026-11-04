import numpy as np,pandas as pd,json,math,datetime as dt
exec(open('review_f/_common.py').read())
# --- ledger N as of the result date
L=pd.read_csv('registry/trial_ledger.csv',dtype=str,keep_default_na=False)
L['n']=pd.to_numeric(L.n_variants,errors='coerce').fillna(0)
def d(x):
    m=pd.to_datetime(str(x)[:10],errors='coerce')
    if pd.isna(m):
        m=pd.to_datetime(str(x)[:7]+'-28',errors='coerce')
    return m
L['dd']=L.date.map(d); print('undated rows',L.dd.isna().sum(),L[L.dd.isna()].n.sum())
for nm,day in (('XM-1-A1/SW-1','2026-10-13'),('EDGE-1-F6','2026-10-14'),('TUNE-1-DIP','2026-10-26')):
    q=L[(L.dd<=pd.Timestamp(day))|L.dd.isna()]; print(nm,'ledger N to date',int(q.n.sum()),'excl analyst',int(q[q.publish_class=='public'].n.sum()))
print(L.sort_values('n',ascending=False).head(6)[['trial_id','n','date']].to_string())
m=load('US500');r=a1(dict(m,sp=.45)).ret.values;print('A1 n',len(r))
for N in (500,1000,1500,2000,3000,5000,10000): print(N,'A1',round(dsr(r,N)[0],3))
# required t at ledger
g=.5772156649;N=178991;E=(1-g)*norm.ppf(1-1/N)+g*norm.ppf(1-1/(N*math.e));print('E[max z] at N',round(E,3),'t needed for DSR .95 (normal)',round(E+1.645,3))
for n in (100,124,397,3284): print('n',n,'per-period SR needed',round((E+1.645)/n**.5,3),'annual Sharpe if daily',round((E+1.645)/n**.5*365**.5,2))
N=114500;print('E N=114500',round((1-g)*norm.ppf(1-1/N)+g*norm.ppf(1-1/(N*math.e)),3))
# 2010-2012 anchors
h=pd.read_csv("@GANN_ROOT@/research/data/xauusd_m1_histdata.csv"); h['ts']=pd.to_datetime(h.time,unit='s',utc=True)
h=h.set_index('ts')
def biggest(day,start,end):
    x=h.loc[f'{day} {start}':f'{day} {end}']
    r=(x.high-x.low); i=r.idxmax(); return str(i)[11:16],round(float(r.max()),2),round(float(r.median()),2)
print('gap-week events: US rule says stamp +1h, EU rule says stamp 0')
for name,day,true_utc in (('NFP 2010-11-05','2010-11-05','12:30'),('NFP 2011-11-04','2011-11-04','12:30'),('NFP 2012-11-02','2012-11-02','12:30'),('FOMC 2010-11-03','2010-11-03','18:15'),('FOMC 2011-03-15','2011-03-15','18:15'),('FOMC 2012-03-13','2012-03-13','18:15'),('CPI 2012-03-16','2012-03-16','12:30')):
    print(name,'true UTC',true_utc,'largest bar stamp',biggest(day,'10:00','21:00'))
# control: same check 2013-2018 in dukascopy-known period
for name,day,true_utc in (('NFP 2015-03-... control US-summer Friday','2013-06-07','12:30'),('NFP winter control','2013-01-04','13:30')):
    print(name,true_utc,biggest(day,'10:00','21:00'))
