"""Generate docs/data_quality.md from results/data_quality.json."""
import json

from .common import ROOT, RESULTS, config


def data_quality():
    q = json.load(open(RESULTS / "data_quality.json"))
    cfg = config()["instruments"]
    L = ["# Data quality report", "",
         "Source: Dukascopy 1-minute bid and ask candles with tick volume, downloaded with",
         "`dukascopy-node` 1.51.1 (`tools/download.py`). Built by `tools/build_data.py`; generated file.", "",
         "**Processing:**",
         "- Bid and ask are joined per minute.",
         "- Mid = (bid+ask)/2, used for signals.",
         "- Spread = max(ask-bid at open, ask-bid at close), used for fills.",
         "- Duplicate timestamps are dropped.",
         "- Bars with high<low or a negative spread are dropped (none found).",
         "- Flat zero-volume padding bars are dropped (none found).",
         "- Bad-tick wicks are clipped to the body/neighbour envelope: more than 25 robust sigmas beyond the body and both neighbouring closes, with price back where it was one bar later.", "",
         "| | " + " | ".join(x["instrument"] for x in q) + " |",
         "|---|" + "---|" * len(q)]
    rows = [("first bar (UTC)", "first_bar_utc"), ("last bar (UTC)", "last_bar_utc"), ("clean 1m bars", "clean_rows"),
            ("duplicate timestamps (bid/ask)", None), ("bid/ask rows without partner", "unmatched_bid_ask"),
            ("bad-tick wicks clipped", "bad_tick_bars_clipped"), ("weekdays in range", "weekdays_in_range"),
            ("weekdays with no 07:00-12:00 London data", "weekdays_no_morning_data"),
            ("...of which Dec 24/25/26/31, Jan 1", "missing_days_on_dec24_25_26_31_jan1"),
            ("weekdays with thin morning data (<80%)", "weekdays_thin_morning_data(<80%)"),
            ("intraday gaps >5 min (07:00-12:00 London)", "morning_gaps_>5min"),
            ("intraday gaps >30 min (07:00-12:00 London)", "morning_gaps_>30min"),
            ("DST-window days without a bar at 08:00 London", "dst_window_days_missing_open_bar"),
            ("median spread 00:00-06:00 London", "spread_med_overnight_0000_0600"),
            ("median spread 07:00-07:59 London", "spread_med_0700_0759"),
            ("median spread 08:00-08:04 London (the open)", "spread_med_0800_0804"),
            ("median spread 08:05-08:29 London", "spread_med_0805_0829"),
            ("median spread 10:00-12:00 London", "spread_med_1000_1200")]
    for label, key in rows:
        if key is None:
            vals = [f'{x["dup_bid"]}/{x["dup_ask"]}' for x in q]
        else:
            vals = []
            for x in q:
                v = x.get(key)
                if isinstance(v, float):
                    v = f"{v:.5g}"
                elif isinstance(v, str) and "+00:00" in v:
                    v = v[:16]
                vals.append(str(v))
        L.append(f"| {label} | " + " | ".join(vals) + " |")
    L += ["", "## Findings", "",
          "1. **Overnight gap on the index CFDs, 2015-01 to about 2018-06.** Dukascopy GER40 and UK100 have essentially no prices between about 20:00 and 06:00 UTC in those years. No Asian box can be built for those days, so Variant A excludes them: the box needs at least 50% minute coverage.",
          "   - About 860 of the 2,691 IS+VAL weekdays are lost.",
          "   - Variant B's London and NY sessions are unaffected. Its Asia session is empty in those years.",
          "   - US30 and NAS100 show the same pattern.",
          "2. **Missing weekdays are exchange holidays.** Examples: Good Friday, Easter Monday, Christmas, New Year, 1 May (Xetra), Whit Monday, German Unity Day (3 Oct).",
          "   - The DST-window days without an open bar are Easter holidays that fall next to the March switch.",
          "   - No DST misalignment was found. The session clock is tested in `tests/test_sessions_robustness.py` and `tests/test_signal.py`.",
          "3. **Spread at the open.** On Dukascopy the index spread is widest overnight and in the hour before the cash open (GER40 ≈ 2.5 points at 07:00-07:59 London). It is already back to its daytime level in the first minutes after 08:00 London (GER40 ≈ 1.4, UK100 ≈ 1.0).",
          "   - Retail brokers often widen for seconds around the open. One-minute data cannot show that, so it is covered by the slippage allowance:",
          "",
          "| | " + " | ".join(cfg) + " |", "|---|" + "---|" * len(cfg),
          "| slippage per side (price units) | " + " | ".join(str(cfg[n]["slip"]) for n in cfg) + " |",
          "| commission per round trip (price units) | " + " | ".join(str(cfg[n]["comm"]) for n in cfg) + " |", "",
          "   - Everything is also run at 0.5x and 2x costs.",
          "4. **GER40 spread regime change.** The median opening spread was about 1.0 point in 2013-2019 and about 1.45 points from 2020 on. Part of the deterioration after 2020 in every config is this cost increase.",
          ""]
    (ROOT / "docs" / "data_quality.md").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    data_quality()
