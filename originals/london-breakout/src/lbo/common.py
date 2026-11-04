"""Shared loading, split guard, and per-instrument context."""
import datetime as dt
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from . import data, features
from . import sessions as S

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"


@lru_cache(maxsize=1)
def config():
    return yaml.safe_load(open(ROOT / "config" / "research.yaml"))


def split_dates():
    s = config()["splits"]
    return dt.date.fromisoformat(s["is_end"]), dt.date.fromisoformat(s["val_end"])


def split_of(dates):
    is_end, val_end = split_dates()
    d = pd.Series(pd.to_datetime(list(dates))).dt.date
    return np.where(d < is_end, "IS", np.where(d < val_end, "VAL", "OOS"))


class Ctx:
    """Everything one instrument needs: 1m arrays, tf bars, volume ratios, daily features.

    allow_oos=False drops every 1m bar from the OOS period so nothing downstream can see it.
    """

    def __init__(self, name, allow_oos=False, tz=S.LON):
        self.name = name
        ic = config()["instruments"][name]
        self.slip, self.comm, self.point = ic["slip"], ic["comm"], ic["point"]
        m = data.load(name)
        if not allow_oos:
            _, val_end = split_dates()
            cut = S.emin(val_end, 0, 0, S.UTC)
            keep = m["t"] < cut
            m = {k: v[keep] for k, v in m.items()}
        self.m = m
        self.tz = tz
        self._bars, self._vr, self._days = {}, {}, {}
        self.daily = features.daily_bars(m, tz)

    def bars(self, tf):
        if tf not in self._bars:
            self._bars[tf] = features.resample(self.m, tf)
        return self._bars[tf]

    def vratio(self, tf):
        if tf not in self._vr:
            self._vr[tf] = features.volume_ratio(self.bars(tf), self.tz)
        return self._vr[tf]
