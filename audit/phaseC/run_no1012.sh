#!/bin/bash
PY=${PY:-python}
export PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0
BASE=$(cd ../_copy && pwd); LOG=$(pwd)/logs_L1
for j in "d_revival sim.py" "d_revival diag.py" "d_revival anomalies.py" "d_revival asia.py" "exit2 exit2.py" "gold_lit gold_lit.py" "price_action pa1.py" "sweep_mtf sweep_mtf.py"; do
 set -- $j; ( cd $BASE/rs_no1012/research/$1; timeout 2400 $PY -B $2 > $LOG/no1012.$1.$2.log 2>&1; echo "no1012 $1 $2 rc=$?" >> $LOG/_status.txt ) &
 while [ $(jobs -r | wc -l) -ge 3 ]; do sleep 1; done
done; wait
