"""Exec e1_pairs.py source in memory (main not called, nothing written), measure month-skip bug and literal-prereg entry band."""
import os,sys,json,numpy as np,pandas as pd
A='@AUDIT@/phaseE/e1_pairs.py'
src=open(A,encoding='utf-8').read().replace('\nmain()\n','\n')
def load(mod):
    s=src
    for a,b in mod: 
        assert a in s,a; s=s.replace(a,b)
    g={'__file__':A,'__name__':'e1x'}; exec(compile(s,'e1x','exec'),g); return g
CHK='or t[f0] > t[s0] - pd.Timedelta(days=form_days if bar_h < 24 else 300):'
base=load([]); 
fixed=load([(CHK,'or t[f0] > t[s0] - pd.Timedelta(days=(form_days-3) if bar_h < 24 else 300):')])
lit=load([(CHK,'or t[f0] > t[s0] - pd.Timedelta(days=(form_days-3) if bar_h < 24 else 300):'),('2 <= abs(zi) < 4','2 <= abs(zi)')])
lib=base['lib']
res={}
for pair,fn,fd,bh,cap in (("XAU/XAG",base['frame_xau_xag'],90,1,240),("BTC/ETH",base['frame_crypto'],90,1,240)):
    d=fn(); d=d[d.index>="2015-01-01"] if pair!="BTC/ETH" else d
    t0,t1=d.index[0],d.index[-1]; c1,c2=lib.cuts(t0,t1)
    per=pd.PeriodIndex(d.index.tz_localize(None),freq='M'); nm=len(set(per))
    # months with enough history
    for nmz,G in (('as_run',base),('skip_fixed',fixed),('skip_fixed+literal_entry',lit)):
        for v in ('V1','V2','V3'):
            tr,m=G['run'](pair,d,v,fd,bh,cap)
            dv=tr[tr.t0<c1] if len(tr) else tr
            r=(dv.gross-dv.cost).values if len(dv) else np.array([])
            res[(pair,nmz,v)]=dict(months=len(m),both=round(float(m.both.mean()),3),valid=round(float(m.valid.mean()),3),n_all=len(tr),n_dev=len(dv),pf_dev=round(lib.pf(r),3) if len(r) else None,pf_gross=round(lib.pf(dv.gross.values),3) if len(r) else None,why=dv.why.value_counts().to_dict() if len(dv) else {})
            print(pair,nmz,v,res[(pair,nmz,v)],flush=True)
    print(pair,'calendar months in frame',nm)
    if pair=="XAU/XAG":
        tr,_=base['run'](pair,d,'V3',fd,bh,cap)
        print('sealed slice trades already on disk V3: t0>=c1',(pd.to_datetime(tr.t0)>=c1).sum(),'>=c2',(pd.to_datetime(tr.t0)>=c2).sum())
        print('mean cost',tr.cost.mean(),'mean gross',tr.gross.mean())
