"""E4 cost basis: event-aware V3/V4 on matrix cost as frozen, using the audit's own spreads file and matrix."""
import json,sys,os,numpy as np,pandas as pd
A='@AUDIT@/phaseE/e4_news.py'
src=open(A,encoding='utf-8').read().replace('if sys.argv[1] == "measure":\n    measure()\nelse:\n    rerun()\n','')
g={'__file__':A,'__name__':'e4x'}; exec(compile(src,'e4x','exec'),g)
ev=g['events'](); et=np.array([e[0] for e in ev]); ety=[e[1] for e in ev]
S=json.load(open('phaseE/e4_spreads.json'))['windows']; cm=g['CostMatrix'].load('_copy/goldbot/results/cost_matrix.json',stat='median',k_slip=.5,commission_per_lot_rt=7.0)
print('events',len(ev),{t:ety.count(t) for t in set(ety)},'cost matrix years',sorted(cm.m['years'].keys())[:3],sorted(cm.m['years'].keys())[-2:])
PF=g['lib'].pf
def ev_sp(ts):
    w=g['in_win'](int(ts.timestamp()),et,ety)
    if not w: return None
    y=min(ts.year,2026);q=S.get(f"{w[0]}|{y}|{w[1]}") or S.get(f"{w[0]}|{y-1}|{w[1]}");return q['p90'] if q else None
for nm in ('v3','v4'):
    t=pd.read_csv(f'phaseC/fable_{nm}_true.csv',parse_dates=['ts'])
    gross=t.pnl.values+20
    med=[];medev=[];inw=0
    for ts in t.ts:
        s=cm.spread_usd(ts);e=ev_sp(ts);inw+=g['in_win'](int(ts.timestamp()),et,ety) is not None
        med.append(100*2*s+7)  # entry hour used both sides, same approximation as gate_table.py
        a=e if e else s; medev.append(100*(a+s)+7)
    med,medev=np.array(med),np.array(medev)
    print(nm,'flat PF',round(PF(t.pnl.values),3),'matrix PF',round(PF(gross-med),3),'matrix + event entry PF',round(PF(gross-medev),3),'mean matrix cost',round(med.mean(),1),'entries in any window',inw)
t=pd.read_csv('phaseC/fable_v3_true.csv',parse_dates=['ts'])
nfp=np.array([e[0] for e in ev if e[1]=='NFP'])
ts=t.ts.astype('int64').values//10**9 if str(t.ts.dtype).endswith('ns, UTC]') else np.array([int(x.timestamp()) for x in t.ts])
dn=[(str(pd.Timestamp(int(x),unit='s')),int(min(abs(x-nfp))/60)) for x in ts if min(abs(x-nfp))<7200]
print('V3 entries within 2h of an NFP',dn)
print('friday 12:00 share',((t.ts.dt.dayofweek==4)&(t.ts.dt.hour==12)).sum())
# 2:1 entry-only factor in code
