#!/bin/bash
# Reruns every goldbot runner in both clock sandboxes. Order follows the dependency on verdict_trades.csv.
PY=${PY:-python}
export PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0
for clock in recorded true; do
(
  cd ../_copy/sb_$clock/research/goldbot/prereg || exit 1
  L=../../../../../phaseC/logs_$clock; mkdir -p $L
  for r in run_verdict hn_runner hp_runner hb_runner sz_runner hv_runner hr_is_runner hr_oos_runner hcrt_runner hsw_runner hm_runner hs_runner; do
    s=$(date +%s); args=""; [ $r = hb_runner ] && args="--tag binding"
    timeout 3000 $PY -B $r.py $args > $L/$r.log 2>&1; rc=$?
    echo "$clock $r rc=$rc $(( $(date +%s)-s ))s" >> $L/_status.txt
  done
) &
done
wait
