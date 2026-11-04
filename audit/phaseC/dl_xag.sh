#!/bin/bash
# Dukascopy XAGUSD M1 bid and ask, written to the audit sandbox only. Tick feed answers 503 at this rate, M1 candles do not.
CLI=@LBO_ROOT@/tools/node_modules/.bin/dukascopy-node.cmd
OUT=@AUDIT@/_copy/data/dk_xag
for y in 2015 2016 2017 2018 2019 2020 2021 2022 2023 2024 2025 2026; do for s in bid ask; do
  f=$OUT/xagusd-$s-$y.csv; [ -f "$f" ] && continue
  d1=$((y+1))-01-01; [ $y = 2026 ] && d1=2026-10-30
  t=$OUT/t_$s$y; mkdir -p $t
  for a in 1 2 3 4; do "$CLI" -i xagusd -from $y-01-01 -to $d1 -t m1 -p $s -v true -f csv -dir "$(cygpath -w $t)" -bs 10 -bp 400 -r 8 -rp 3000 -s > /dev/null 2>&1; g=$(ls $t/*.csv 2>/dev/null | head -1); [ -n "$g" ] && { mv "$g" "$f"; break; }; sleep 60; done
  rmdir $t 2>/dev/null; echo "$s $y $( [ -f $f ] && wc -l < $f )"
done; done
