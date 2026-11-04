#!/bin/bash
PY=${PY:-python}
export PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0
LOG=$(pwd)/logs_L1
for c in recorded true; do
  ( cd ../_copy/sb_fable_$c; PYTHONPATH=. timeout 1500 $PY -B research/fleet_review/london_tp_backtest.py > $LOG/$c.frl.log 2>&1; echo "$c.frl2 rc=$?" >> $LOG/_status.txt
    PYTHONPATH=. timeout 900 $PY -B research/dr_backtest/run_1pz.py > $LOG/$c.run_1pz.log 2>&1; echo "$c.run_1pz rc=$?" >> $LOG/_status.txt ) &
done
wait
