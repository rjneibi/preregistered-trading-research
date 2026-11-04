#!/bin/bash
PY=${PY:-python}
export PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 PYTHONPATH=src
L=$(pwd)/logs_L1
( cd ../_copy/crt_fvg; PYTHONPATH=. timeout 3000 $PY -B run.py grid select full analyse > $L/crt_fvg_all.log 2>&1; echo "crt rc=$?" >> $L/_status.txt ) &
( cd ../_copy/lbo; export PYTHONPATH="src${PSEP:-;}../stubs"; for s in grids analyze deep freeze oos; do timeout 3000 $PY -B run_all.py --stage $s > $L/lbo_$s.log 2>&1; echo "lbo $s rc=$?" >> $L/_status.txt; done ) &
wait
