#!/bin/bash
PY=${PY:-python}
export PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0
BASE=$(cd ../_copy && pwd); LOG=$(pwd)/logs_talab; mkdir -p $LOG
for v in gap2; do for r in "round1.py M5" round2.py round4.py round5.py round6.py round8.py round9.py round11.py round12.py; do
 ( cd $BASE/rs_$v/research/ta_lab; timeout 900 $PY -B $r > $LOG/$v.$(echo $r | tr ' .' '__').log 2>&1; echo "$v $r rc=$?" >> $LOG/_status.txt ) &
 while [ $(jobs -r | wc -l) -ge 5 ]; do sleep 1; done
done; done; wait
