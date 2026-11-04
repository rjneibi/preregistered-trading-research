"""Run from audit/stats with the audit venv. The forward rule code must reproduce A1 and IBS on the audited bars at the audited spread."""
import importlib.util,sys,re,json,numpy as np
sys.argv=['x']
src=open('../forward/forward_update.py',encoding='utf-8').read().replace('\nmain()\n','\n').replace('HERE = os.path.dirname(os.path.abspath(__file__))',"HERE = '../forward'")
g={}; exec(compile(src,'fw','exec'),g)
s=open('pass_audit.py',encoding='utf-8').read()
s=s[:s.rindex('main()')] if s.rstrip().endswith('main()') else s.split('if __name__')[0]
p={'__file__':'pass_audit.py','__name__':'pa'}; exec(compile(s,'pa','exec'),p)
us=p['load']('US500'); print({k:(v if np.isscalar(v) else len(v)) for k,v in us.items()})
sp=us.get('sp') or us.get('spread')
m={k:us[k] for k in 't o h l c'.split()}
if m['t'].dtype.kind=='M': m['t']=m['t'].astype('datetime64[s]').astype(np.int64)
d=g['dip'](m,sp if np.isscalar(sp) else float(np.median(sp)),0.05/365)
r=np.array([x[3] for x in d]); print('fw dip',len(d),round(r[r>0].sum()/-r[r<0].sum(),3))
t=p['a1'](us); rr=p['ret'](t); print('pa a1',len(t),round(p['pf'](rr),3)); print(t[0] if len(t) else None)
b=g['ibs'](m,sp if np.isscalar(sp) else float(np.median(sp)),0.05/365); r=np.array([x[3] for x in b]); print('fw ibs',len(b),round(r[r>0].sum()/-r[r<0].sum(),3))
t=p['ibs_rule'](us); rr=p['ret'](t); print('pa ibs',len(t),round(p['pf'](rr),3))
for k in ('US500','US30','US2000','USTEC'):
    print(k, p['load'](k)['sp'])
