#!/bin/bash
# Partial cost matrix from commit 977fff5, for the runners whose stored output predates the full-coverage matrix.
PY=${PY:-python}
export PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0
cd ../_copy/sb_partial/research/goldbot/prereg
L=../../../../../phaseC/logs_partial; mkdir -p $L
for r in run_verdict hp_runner hr_is_runner hr_oos_runner sz_runner hm_runner hs_runner; do
  s=$(date +%s); timeout 3000 $PY -B $r.py > $L/$r.log 2>&1; echo "partial $r rc=$? $(( $(date +%s)-s ))s" >> $L/_status.txt
done
