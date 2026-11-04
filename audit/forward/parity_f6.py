"""Run from audit/stats with the goldbot venv. Forward F6 against the audited F6 on the same closes from 2024."""
import os,sys,numpy as np,pandas as pd
HERE=os.getcwd(); AUD=os.path.dirname(HERE)
s=open('pass_audit.py',encoding='utf-8').read().replace("\nmain()\n","\n")
pa={"__file__":os.path.join(HERE,"pass_audit.py"),"__name__":"pa"}; exec(compile(s,"pa","exec"),pa)
sys.path[:0]=[pa["SB"]+"/cross_market"]
import edge_lab
cl=edge_lab.crypto_close(); o,_=edge_lab.f6()[:2] if isinstance(edge_lab.f6(),tuple) else (edge_lab.f6(),None)
print(cl.index[-1],list(cl.columns),type(o),len(o))
src=open('../forward/forward_update.py',encoding='utf-8').read().replace('\nmain()\n','\n').replace('HERE = os.path.dirname(os.path.abspath(__file__))',"HERE = '../forward'")
g={}; exec(compile(src,'fw','exec'),g)
c2=cl[cl.index>='2024-01-01']
def stub(co):
    k=[x for x in cl.columns if x==co or x.startswith(co)][0]
    v=c2[k].dropna(); return dict(t=(pd.DatetimeIndex(v.index).asi8//10**(9 if str(pd.DatetimeIndex(v.index).dtype).endswith('[ns]') else 6 if '[us]' in str(pd.DatetimeIndex(v.index).dtype) else 0)).astype(np.int64),c=v.values)
g['binance']=stub
rows=g['f6']([str(x).replace('USDT','') for x in cl.columns],0.001)
f=pd.Series([r[3] for r in rows],index=pd.to_datetime([r[1] for r in rows]))
o=pd.Series(np.asarray(o),index=pd.DatetimeIndex(o.index)) if hasattr(o,'index') else None
j=f.to_frame('f').join(o.rename('o'),how='inner').dropna()
print(len(j),'corr',j.corr().iloc[0,1],'max abs diff',(j.f-j.o).abs().max(),'sum',j.f.sum(),j.o.sum())
