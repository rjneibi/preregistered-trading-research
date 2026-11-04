import numpy as np,glob,os
for d in ("@GANN_ROOT@/research/cross_market/data","@GANN_ROOT@/research/cross_market/data_edge"):
    for p in sorted(glob.glob(d+"/*_D1.npz")):
        z=np.load(p); c=z['c'].astype(float);o=z['o'].astype(float);t=z['t']
        if len(c)<50: continue
        r=o[1:]/c[:-1]; k=np.flatnonzero((r>1.3)|(r<.72))
        if len(k) and not any(x in os.path.basename(p) for x in ('USDT','BTC','ETH')):
            print(os.path.basename(p),len(c),[(str(np.datetime64(int(t[i+1]),'s'))[:10],round(float(r[i]),3)) for i in k][:6])
