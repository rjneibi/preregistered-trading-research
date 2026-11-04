import pandas as pd,re,json,csv
L=pd.read_csv('registry/trial_ledger.csv',dtype=str,keep_default_na=False)
print(len(L),L.columns.tolist())
L['n']=pd.to_numeric(L.n_variants,errors='coerce')
print('blank/non numeric',L[L.n.isna()][['trial_id','n_variants','label']].to_string())
print('zero rows');print(L[L.n==0][['trial_id','programme_or_family','label','outcome','count_basis']].to_string(max_colwidth=60))
print('sum',L.n.sum(),'top');print(L.sort_values('n',ascending=False).head(14)[['trial_id','n','label','count_basis','publish_class']].to_string(max_colwidth=70))
print(L.count_basis.value_counts().head(20))
print('dup ids',L.trial_id.duplicated().sum())
print('dup labels',L[L.label.duplicated(keep=False)][['trial_id','label','n']].to_string(max_colwidth=50))
y=open('registry/experiments.yaml',encoding='utf-8').read()
ent=re.split(r'^- id: ',y,flags=re.M)[1:]
E={}
for e in ent:
    i=e.split('\n')[0].strip(); m=re.search(r'^  n_variants: (.+)$',e,re.M); E[i]=m.group(1).strip() if m else None
Y=pd.Series(E); print('yaml entries',len(Y))
miss=[i for i in Y.index if i not in set(L.trial_id)]; print('registry ids not in ledger',miss)
m2=L[~L.trial_id.isin(Y.index)]; print('ledger rows not in registry',len(m2),m2.programme_or_family.value_counts().to_dict())
c=L[L.trial_id.isin(Y.index)].set_index('trial_id')
diff=[(i,E[i],c.n[i]) for i in c.index if str(E[i]).replace("'","")!=str(c.n_variants[i]).replace('.0','')]
print('mismatch',diff)
print('yaml numeric sum',pd.to_numeric(Y.str.replace("'",''),errors='coerce').sum())
