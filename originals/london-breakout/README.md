# London Breakout: edge study

This project tests whether the "London Breakout" strategy has an edge. It takes the Asian-box version from a social post (Variant A) and the "elitrade basic" PDF version (Variant B), and runs both on DAX (GER40) and FTSE (UK100) with 13 years of Dukascopy 1-minute bid/ask data. US30, NAS100, EURUSD, GBPUSD and XAUUSD serve as robustness checks.

**Verdict: no edge after costs. Abandon.**
- The frozen config made -0.008R per trade on the locked 2024-2026 out-of-sample data (n=204).
- On in-sample + validation it made -0.031R.
- All six pre-registered gates fail.

See `report.html`.

## Run everything

```
pip install -r requirements.txt          # Python 3.11; numpy/pandas/scipy/matplotlib/pyyaml/pytest/tabulate
python run_all.py                        # download (skipped if data/raw exists) -> ... -> report.html
```

Single stages:
```
python run_all.py --stage report
```

The stages are: `download`, `data`, `test`, `grids`, `analyze`, `deep`, `freeze`, `oos`, `docs`, `report`.

**Requirements**
- Node 18+ for the downloader (`tools/package.json` pins `dukascopy-node` 1.51.1).
- The full download takes about 20 minutes. It produces about 3 GB of CSV in `data/raw/`, which is not in git.
- The grids take about 30 minutes on 6 cores.

**Configuration and reproducibility**
- Everything is driven by `config/research.yaml`: instruments, costs, splits, grids and seeds.
- The random seed is fixed (`seed: 20261030`).
- `oos` refuses to run a second time. To force it, delete `results/oos_*.json`, and say why in `RESEARCH_LOG.md`.

## Layout

| Path | What |
|---|---|
| `config/research.yaml` | the single config for the research |
| `config/final_strategy.yaml` | the frozen rules, every parameter explicit (status: failed validation) |
| `strategy/signal.py` | standalone live signal module: bars in, entry/stop/target or no-trade out |
| `src/lbo/` | engine, sessions (zoneinfo), variants A/B, grids, robustness, analysis, report |
| `tests/` | hand-computed fill cases, DST/session clock, robustness statistics, signal-module edge cases, and a bar-by-bar replay test proving the live module matches the backtest |
| `docs/research_summary.md` | literature and prior backtests, hypotheses H1-H15 |
| `docs/data_quality.md` | gaps, duplicates, bad ticks, holidays, DST, spreads at the open |
| `docs/gaps.md` | every weakness found and the fixes tried |
| `RESEARCH_LOG.md` | decisions in order, including gates frozen before results were viewed |
| `results/` | every intermediate result (stage-1 tables, deep dives, walk-forward, OOS) |
| `data/calendar/high_impact_events.csv` | NFP, US CPI, ECB (2013-2026), BoE (2024+) |

## Using `strategy/signal.py` in a bot

```python
from strategy.signal import load_params, decide, finalize, on_bar
p = load_params("config/final_strategy.yaml")
d = decide(bars_1m_utc, now_utc, p, trades_taken_today=n)    # call once per closed signal bar
if d.action == "ENTER":
    pos = finalize(d, fill_mid)                              # exact stop / target for the real fill
# each closed 1m bar:
why, px = on_bar(pos, bar)                                   # STOP / TARGET / TIME / None
```

The module only signals on the bar that has just closed. A missed signal is reported as stale and is never chased.

The research found no edge, so this module is a reference implementation. It is not a recommendation to trade.
