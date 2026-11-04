"""Minimal histogram gradient-boosted trees (logistic loss) in numpy - stands in for sklearn's
HistGradientBoostingClassifier, whose compiled DLLs are blocked by Windows Application Control."""
import numpy as np


class GBM:
    def __init__(self, n_iter=200, lr=0.05, depth=3, bins=32, min_leaf=200, lam=1.0):
        self.n_iter, self.lr, self.depth, self.nb = n_iter, lr, depth, bins
        self.min_leaf, self.lam = min_leaf, lam

    def _bin(self, X):
        return np.stack([np.searchsorted(e, X[:, f], side="right") for f, e in enumerate(self.edges)], 1)

    def fit(self, X, y):
        self.edges = [np.unique(np.quantile(X[:, f], np.linspace(0, 1, self.nb + 1)[1:-1])) for f in range(X.shape[1])]
        B = self._bin(X)
        n, F = B.shape
        p0 = np.clip(y.mean(), 1e-4, 1 - 1e-4)
        self.base = np.log(p0 / (1 - p0))
        raw = np.full(n, self.base)
        self.trees = []
        for _ in range(self.n_iter):
            p = 1 / (1 + np.exp(-raw))
            g, h = p - y, p * (1 - p)
            node = np.zeros(n, dtype=np.int64)
            splits = []                                   # per level: {node: (feature, bin)}
            for lev in range(self.depth):
                nn = 2 ** lev
                best = {}
                for f in range(F):
                    key = node * (self.nb + 1) + B[:, f]
                    sz = nn * (self.nb + 1)
                    G = np.bincount(key, g, sz).reshape(nn, -1)
                    Hh = np.bincount(key, h, sz).reshape(nn, -1)
                    N = np.bincount(key, None, sz).reshape(nn, -1)
                    GL, HL, NL = G.cumsum(1), Hh.cumsum(1), N.cumsum(1)
                    Gt, Ht, Nt = GL[:, -1:], HL[:, -1:], NL[:, -1:]
                    GR, HR, NR = Gt - GL, Ht - HL, Nt - NL
                    gain = GL ** 2 / (HL + self.lam) + GR ** 2 / (HR + self.lam) - Gt ** 2 / (Ht + self.lam)
                    gain[(NL < self.min_leaf) | (NR < self.min_leaf)] = -1
                    for q in range(nn):
                        b = int(np.argmax(gain[q]))
                        if gain[q, b] > 0 and gain[q, b] > best.get(q, (0, 0, 0))[2]:
                            best[q] = (f, b, gain[q, b])
                splits.append({q: (f, b) for q, (f, b, _) in best.items()})
                newnode = node * 2
                for q, (f, b) in splits[-1].items():
                    m = node == q
                    newnode[m] += (B[m, f] > b)
                node = newnode
            nl = 2 ** self.depth
            G = np.bincount(node, g, nl)
            Hh = np.bincount(node, h, nl)
            leaf = -G / (Hh + self.lam) * self.lr
            self.trees.append((splits, leaf))
            raw += leaf[node]
        return self

    def predict_proba(self, X):
        B = self._bin(X)
        raw = np.full(len(B), self.base)
        for splits, leaf in self.trees:
            node = np.zeros(len(B), dtype=np.int64)
            for lev in splits:
                newnode = node * 2
                for q, (f, b) in lev.items():
                    m = node == q
                    newnode[m] += (B[m, f] > b)
                node = newnode
            raw += leaf[node]
        p = 1 / (1 + np.exp(-raw))
        return np.stack([1 - p, p], 1)


def auc(y, s):
    o = np.argsort(s)
    r = np.empty(len(s))
    r[o] = np.arange(1, len(s) + 1)
    n1 = y.sum()
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * (len(y) - n1))
