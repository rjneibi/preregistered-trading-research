#!/bin/bash
PY=${PY:-python}
export PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0
LOG=$(pwd)/logs_L1
for c in recorded true; do
  ( $PY -B frm_partial.py $c > $LOG/$c.frm_partial.log 2>&1; echo "$c.frm_partial rc=$?" >> $LOG/_status.txt ) &
  ( cd ../_copy/sb_fable_$c; timeout 1500 $PY -B research/fleet_review/london_tp_backtest.py > $LOG/$c.frl.log 2>&1; echo "$c.frl rc=$?" >> $LOG/_status.txt ) &
done
wait
