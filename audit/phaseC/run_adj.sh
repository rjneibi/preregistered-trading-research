#!/bin/bash
PY=${PY:-python}
export PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0
BASE=$(cd ../_copy && pwd); LOG=$(pwd)/logs_L1
for j in "cross_market xm_lab.py" "cross_market a1_stress.py" "cross_market swing_lab.py" "cross_market vs_lab.py" "cross_market edge_lab.py" "cross_market combo.py" "tune1 tune_dip.py final"; do
 set -- $j; ( cd $BASE/rs_adj/research/$1; timeout 2400 $PY -B $2 $3 > $LOG/adj.$1.$2.log 2>&1; echo "adj $1 $2 rc=$?" >> $LOG/_status.txt ) &
 while [ $(jobs -r | wc -l) -ge 3 ]; do sleep 1; done
done; wait
