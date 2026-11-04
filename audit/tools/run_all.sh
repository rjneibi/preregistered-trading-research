#!/bin/bash
# All stages, in dependency order, inside the clean clone. A failed stage is recorded and the run goes on, so the report shows everything that did not reproduce.
set -u
export PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0
A=$(pwd)
L=$A/tools/clean_logs; mkdir -p "$L"
: > "$L/_stages.txt"
st() { # name, then command
  n=$1; shift; s=$(date +%s)
  if [ "${TIER:-full}" = public ] && grep -qx "$n" "$A/tools/stages_broker.txt"; then ( "$@" ) > "$L/$n.log" 2>&1; echo "$n rc=expected-$? $(( $(date +%s)-s ))s" >> "$L/_stages.txt"; return; fi
  ( "$@" ) > "$L/$n.log" 2>&1
  echo "$n rc=$? $(( $(date +%s)-s ))s" >> "$L/_stages.txt"
}
cd "$A"
st sources $PA -B tools/copy_sources.py "$SRC"
cd "$A/phaseC"
st sb_goldbot $PY -B sandbox_goldbot.py
st sb_fable $PY -B sandbox_fable.py
st sb_partial $PY -B sandbox_partial.py
st sb_research $PY -B sandbox_research.py
st sb_extra $PY -B ../tools/sandbox_extra.py
st sb_paths $PY -B sandbox_paths.py
cd "$A"
st kat $PY -B -m pytest -q -p no:cacheprovider engine/test_kat.py
st cross_engines $PY -B engine/cross_engines.py
cd "$A/infrastructure"
for f in data_profile clock_cross resample_and_defects lookahead; do st b_$f $PY -B $f.py; done
st b_look0 bash -c "cp lookahead.json _m1.json && LOOK_MARGIN=0 $PY -B lookahead.py && cp lookahead.json lookahead_margin0.json; mv _m1.json lookahead.json"
cd "$A/phaseC"
rm -f logs_L1/*.rc
for f in logs*/_status.txt; do : > "$f"; done
st goldbot_both bash run_goldbot_both.sh
st goldbot_partial bash run_goldbot_partial.sh
st h1_clock $PY -B h1_clock.py
for c in recorded true; do st fable_$c $PY -B fable_both.py $c; st fade_$c $PY -B fade_both.py $c; done
st dr_flip bash run_dr_flip.sh
st fr bash run_frl.sh
st l1_queue bash run_l1_queue.sh
st combo5 bash -c "cd ../_copy/rs_recorded/research/cross_market && $PY -B combo5.py > ../../../../phaseC/logs_L1/recorded.cross_market.combo5.log 2>&1"
st lbo_crt bash run_lbo_crt.sh
st talab_gap_make $PY -B talab_gap.py
st talab_gap_run bash run_talab_gap.sh
st talab_pess_make $PY -B talab_pess.py
st talab_pess_run bash run_talab_pess.sh
st talab_pess_rep $PA -B talab_pess_report.py
st no1012_make $PA -B sandbox_no1012.py
st no1012_run bash run_no1012.sh
st adj_make $PA -B split_fix.py
st adj_run bash run_adj.sh
for f in clock_map clock_map_all clock_anchors lookahead2 gap_asymmetry l2_recompute l2_more dr_matrix; do st c_$f $PY -B $f.py; done
for c in recorded true; do st c_frm_$c $PY -B frm_partial.py $c; done
for f in compare_goldbot goldbot_table; do st c_$f $PY -B $f.py; done
cd "$A"
st pass_audit $PY -B stats/pass_audit.py
st sc1 $PY -B trade_checks/sc1_check.py
st spot $PY -B trade_checks/spot_checks.py
cd "$A/_copy/tvsearch" && st tvs_p2 "$PA" -B src/phase2.py
cd "$A/phaseC" && st tvs_recheck $PA -B tvs_recheck.py
cd "$A/_copy/labelsizing" && st labelsizing "$PL" -B run_validation.py
cd "$A/phaseD" && st h3_build $PA -B h3_run.py build && st h3_run $PA -B h3_run.py run
cd "$A/phaseE"
st e2_prep $PA -B e2_silver.py prep
st e1 $PA -B e1_pairs.py
PYTHONPATH=. st e2_fable $PY -B fable_xag.py xag
PYTHONPATH=. st e2_score $PY -B e2_silver.py score
st e3 $PY -B e3_portfolio.py
st e4m $PA -B e4_news.py measure
st e4r $PA -B e4_news.py rerun
st e5 $PY -B e5_crypto.py
PYTHONPATH=. st e6 $PY -B e6_paper.py
st e7 $PA -B e7_indicators.py
cd "$A"
st trial $PA -B stats/trial_count.py
st assumed $PA -B stats/assumed_clock.py
st gate bash -c "cd stats && $PY -B gate_table.py"
st verdicts $PA -B phaseC/build_verdicts.py
st trace $PA -B stats/traceability.py
