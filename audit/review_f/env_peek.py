import numpy as np, glob
z=np.load("@LBO_ROOT@/data/m1/XAUUSD.npz")
print({k:(z[k].shape,z[k].dtype,z[k][:3],z[k][-2:]) for k in z.files})
print('sp stats',np.nanmedian(z['sp']),np.nanpercentile(z['sp'],[1,99]))
z=np.load("@GANN_ROOT@/research/cross_market/data/US500_D1.npz")
print({k:(z[k].shape,z[k].dtype,z[k][:2],z[k][-2:]) for k in z.files})
import datetime
print(datetime.datetime.utcfromtimestamp(int(z['t'][0])),datetime.datetime.utcfromtimestamp(int(z['t'][-1])))
print(np.diff(z['t'])[:10], (np.diff(z['t'])<=0).sum(), 'dupes',len(z['t'])-len(np.unique(z['t'])))
print('sp',np.unique(z['sp'])[:10], np.median(z['sp'][z['sp']>0]) if (z['sp']>0).any() else None)
