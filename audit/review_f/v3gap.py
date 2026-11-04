import pandas as pd,numpy as np,re
s=open('review_f/v3.py',encoding='utf-8').read()
s=s[:s.index("A=run(pd.Timestamp('2015-06-19'")]
s=s.replace("""                    if (L[i]<=sl if sg>0 else H[i]>=sl): pnl=sg*(sl-f);why='sl';break
                    if (H[i]>=tp if sg>0 else L[i]<=tp): pnl=sg*(tp-f);why='tp';break""","""                    if i>i0 and (O[i]<=sl if sg>0 else O[i]>=sl): pnl=sg*(O[i]-f);why='gsl';break
                    if i>i0 and (O[i]>=tp if sg>0 else O[i]<=tp): pnl=sg*(O[i]-f);why='gtp';break
                    if (L[i]<=sl if sg>0 else H[i]>=sl): pnl=sg*(sl-f);why='sl';break
                    if (H[i]>=tp if sg>0 else L[i]<=tp): pnl=sg*(tp-f);why='tp';break""")
exec(s)
A=run(pd.Timestamp('2015-06-19',tz='UTC'),pd.Timestamp('2021-06-18 23:59',tz='UTC'))
B=run(pd.Timestamp('2021-06-19',tz='UTC'),pd.Timestamp('2026-06-19 17:57',tz='UTC'))
T=pd.concat([A,B]);p=T.pnl.values;print('gap fills both sides n',len(p),'PF',round(p[p>0].sum()/-p[p<0].sum(),3),'net',round(p.sum()),T.why.value_counts().to_dict())
