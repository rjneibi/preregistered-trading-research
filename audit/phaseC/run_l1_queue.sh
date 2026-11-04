#!/bin/bash
# Reproduction queue, unchanged code in sandboxes. One log per run. Five at a time. Original outputs are not touched.
PY=${PY:-python}
export PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0
BASE=$(cd ../_copy && pwd)
LOG=$(pwd)/logs_L1; mkdir -p $LOG
job() {  # clock dir script args...
  c=$1; d=$2; s=$3; shift 3
  tag=$c.$(echo $d | tr / _).$(echo $s $* | tr ' /.' '___')
  [ -f "$LOG/$tag.rc" ] && [ "$(cat "$LOG/$tag.rc")" = 0 ] && return
  cd "$BASE/rs_$c/research/$d" || exit 1
  st=$(date +%s)
  timeout 2400 $PY -B $s "$@" > "$LOG/$tag.log" 2>&1
  rc=$?
  echo $rc > "$LOG/$tag.rc"
  echo "$tag rc=$rc $(( $(date +%s)-st ))s" >> "$LOG/_status.txt"
}
export -f job; export PY BASE LOG
cat <<'EOF' | xargs -P 5 -L 1 bash -c 'job "$@"' _
recorded ta_lab round1.py M5
recorded ta_lab round2.py
recorded ta_lab round4.py
recorded ta_lab round5.py
recorded ta_lab round6.py
recorded ta_lab round8.py
recorded ta_lab round9.py
recorded ta_lab round11.py
recorded ta_lab round12.py
recorded d_revival sim.py
recorded d_revival diag.py
recorded d_revival ml_lab.py
recorded d_revival news_lab.py
recorded d_revival asia.py
recorded d_revival asia2.py
recorded d_revival anomalies.py
recorded d_revival split.py
recorded d_revival gbm.py
recorded d_revival news_slip.py
recorded exit2 exit2.py
recorded exit2 forensics.py
recorded exit2 own_sweep.py
recorded gold_lit gold_lit.py
recorded price_action pa1.py
recorded price_action ib_confirm.py
recorded price_action ib_diag.py
recorded price_action dollars.py
recorded price_action recent.py
recorded pa_lab pa1.py
recorded pa_lab pa30.py
recorded sweep_mtf sweep_mtf.py
recorded cross_market xm_lab.py
recorded cross_market a1_stress.py
recorded cross_market swing_lab.py
recorded cross_market scalp_lab.py
recorded cross_market vs_lab.py
recorded cross_market crypto_lab.py
recorded cross_market crypto_twin.py
recorded cross_market edge_lab.py
recorded cross_market f6_stress.py
recorded cross_market combo.py
recorded cross_market profit.py
recorded tune1 tune_dip.py dev
recorded tune1 tune_dip.py final
recorded tune1 tune_orb.py dev
recorded tune1 tune_orb.py final
recorded powell powell_lab.py --oos
recorded powell powell_verdict.py
true d_revival sim.py
true d_revival diag.py
true d_revival ml_lab.py
true exit2 exit2.py
true gold_lit gold_lit.py
true price_action pa1.py
true price_action ib_confirm.py
true sweep_mtf sweep_mtf.py
EOF
