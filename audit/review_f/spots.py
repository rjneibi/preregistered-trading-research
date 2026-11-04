import json,re,pandas as pd,numpy as np
J=lambda f:json.load(open(f))
PF=lambda p:(lambda a:a[a>0].sum()/-a[a<0].sum())(np.asarray(p,float))
out=[]
def chk(name,claim,val,ok=None):
    if ok is None:
        try: ok=abs(float(claim)-float(val))<=0.51*10**(-len(str(claim).split('.')[-1]) if '.' in str(claim) else 0)
        except: ok=str(claim)==str(val)
    out.append((name,claim,val,'OK' if ok else 'MISMATCH'))
h=pd.read_csv('phaseC/h1_true_utc_trades.csv',parse_dates=['entry_ts','exit_ts'])
chk('H1 true n',481,len(h)); chk('H1 true PF',1.009,PF(h.net_med)); chk('H1 p90',0.933,PF(h.net_p90))
chk('H1 old',0.831,PF(h[h.era=='old'].net_med)); chk('H1 new',1.114,PF(h[h.era=='new'].net_med))
c=h.net_med.cumsum(); chk('H1 maxDD',11291,(c.cummax()-c).max())
hc=J('phaseC/h1_clock.json'); chk('H1 rec PF',1.130,hc['recorded_clock']['median']['full']['pf']); chk('H1 rec p90',1.045,hc['recorded_clock']['p90']['full']['pf']); chk('H1 rec DD',7108,hc['recorded_clock']['median']['full']['maxdd_usd']); chk('H1 pos splits rec',11,hc['recorded_clock']['splits_pos']); chk('H1 pos splits true',8,hc['true_utc']['splits_pos'])
be=hc['true_utc']['by_entry_hour'] if 'by_entry_hour' in hc['true_utc'] else {}
v3=pd.read_csv('phaseC/fable_v3_true.csv');v4=pd.read_csv('phaseC/fable_v4_true.csv')
chk('V4 n',577,len(v4));chk('V4 PF',1.145,PF(v4.pnl));chk('V4 net',20185,v4.pnl.sum())
y=v4[v4.ts.str.startswith('2025')];chk('V4 2025 n',52,len(y));chk('V4 2025 win',76.9,100*(y.pnl>0).mean());chk('V4 2025 PF',1.13,PF(y.pnl));chk('V4 2025 net',3338,y.pnl.sum())
v4r=pd.read_csv('phaseC/fable_v4_recorded.csv');y=v4r[v4r.ts.str.startswith('2025')];chk('V4 rec 2025 win',86.3,100*(y.pnl>0).mean());chk('V4 rec 2025 PF',2.90,PF(y.pnl));chk('V4 rec PF',1.331,PF(v4r.pnl));chk('V4 rec net',39875,v4r.pnl.sum())
v3r=pd.read_csv('phaseC/fable_v3_recorded.csv');chk('V3 rec PF',1.667,PF(v3r.pnl));chk('V3 rec net',70596,v3r.pnl.sum());c=v3r.pnl.cumsum();chk('V3 rec DD',6935,(c.cummax()-c).max())
R='_copy/sb_true/research/goldbot/results/'
hb=J(R+'HB_run_binding.json');print(list(hb.keys())[:30]);chk('H-B PF',1.040,hb['pf']);chk('H-B old',0.847,hb['pf_old']);chk('H-B splits',9,hb['splits_positive']);chk('H-B p90',0.989,hb['pf_p90'])
hn=J(R+'HN_run.json');print('HN keys',list(hn.keys())[:20]);hp=J(R+'HP_run.json');print('HP',list(hp.keys())[:20]);hm=J(R+'HM_run.json');print('HM',list(hm.keys())[:20]);hr=J(R+'HR_oos_run.json');print('HR',list(hr.keys())[:20]);hs=J(R+'HS_run.json');print('HS',list(hs.keys())[:20])
gc=J('phaseC/goldbot_compare.json');print(json.dumps(gc['HN_run.json'])[:500])
dr=J('phaseC/dr_matrix.json');chk('DR D true matrix',1.099,dr['true D median']['pf']);chk('DR D true p90',1.001,dr['true D p90']['pf']);chk('DR D rec',0.974,dr['recorded D median']['pf']);chk('DR R true',0.780,dr['true R median']['pf'])
l2=J('phaseC/l2_recompute.json');print('door3',l2['door3 true_utc'],l2['door3 recorded'],l2['door3 stored']);print('cycles',json.dumps(l2['cycles true_utc'])[:500],json.dumps(l2['cycles recorded'])[:400])
df=J('phaseC/deferred_checks.json');chk('H1 measured PF',0.952,df['h1_costs']['pf_measured'])
sc=J('trade_checks/sc1_check.json');chk('SC PF',1.259,sc['pf']);chk('SC real',1.247,sc['fills']['real_entry']);chk('SC twin',0.0025,sc['twin_flip_p']);chk('SC DSR18',0.81,sc['dsr']['18'][0]);chk('SC DSRledger',0.03,sc['dsr']['114500'][0]);chk('SC 2026',.88,sc['by_year']['2026']['pf']);chk('SC beyond',3.2,sc['entry_beyond_edge_share']*100)
tv=J('phaseC/tvs_recheck.json');print('tvs',{k:tv[k] for k in tv if k not in('by_cell','mismatch_examples')})
ta=J('phaseC/talab_pess.json');print('talab',json.dumps(ta['summary'])[:400])
ca=J('phaseC/clock_anchors.json');print('anch',json.dumps({k:ca[k] for k in ('fomc_n','share_shifted','A_fomc','D_monthly','E_switch_days')})[:1100])
cm=J('phaseC/clock_map_all.json');print('fixed',cm['histdata_fixed']['days'],cm['histdata_fixed']['lags'],cm['histdata_fixed']['low_corr'],'raw segs',cm['histdata_raw']['n_segments'])
fr=J('phaseC/e5') if False else None
e5f=J('phaseE/e5_result_first_run.json')
print('E5 first',{t:[k for k,v in e5f['CR1_trend'][t].items() if isinstance(v,dict) and any('pass' in x and v[x] is True for x in v)] for t in e5f['CR1_trend']},{t:[k for k,v in e5f['CR1_swing'][t].items() if isinstance(v,dict) and any('pass' in x and v[x] is True for x in v)] for t in e5f['CR1_swing']})
# verdict table counts
L=[l for l in open('VERDICTS.md',encoding='utf-8') if l.startswith('| ') and '**' in l]
import collections
print(collections.Counter(re.search(r'\*\*([A-Z-]+)\*\*',l).group(1) for l in L if re.search(r'\*\*([A-Z-]+)\*\*',l)),len(L))

hn=J(R+'HN_run.json');chk('H-N PF',0.914,hn['news_pf_med']);chk('H-N n',65,hn['n_news'])
chk('H-P PF',1.033,hp['portfolio'].get('pf_med',hp['portfolio'].get('pf')));print(hp['portfolio'])
chk('HR routed',1.075,hr['routed_pf']);chk('HR uplift',0.007,hr['uplift']);print('HM',hm['pooled']);print('HS',hs['winner_oos'])
ck=J('phaseC/clock_anchors.json');m=np.array([x[4] for x in ck['D_monthly']],float);print('months',len(m),'min corr',m.min(),'all lag0',all(x[3]==0 for x in ck['D_monthly']));print('switch',ck['E_switch_days'] if not isinstance(ck['E_switch_days'],list) else len(ck['E_switch_days']))
print({k:hc['true_utc'].get(k) for k in hc['true_utc'] if k!='median' and k!='p90'})
for x in out: print(x)
print('mismatch',[x for x in out if x[3]!='OK'],'checked',len(out))
