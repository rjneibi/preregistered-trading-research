#!/bin/bash
PY=${PY:-python}
export PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0
LOG=$(pwd)/logs_L1
for c in recorded true; do
( cd ../_copy/sb_fable_$c
  for s in research/dr_backtest/run.py research/fleet_review/micro_grid_backtest.py; do
    n=$c.$(basename $s .py); timeout 1500 $PY -B $s > $LOG/$n.log 2>&1; echo "$n rc=$?" >> $LOG/_status.txt
  done ) &
done
wait
for c in recorded true; do cp ../_copy/sb_fable_$c/research/dr_backtest/backtest_report.md $LOG/$c.dr_backtest_report.md; done
