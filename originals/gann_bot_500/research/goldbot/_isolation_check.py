"""Quarantine guard for the goldbot research artifact.

Run this *inside* the research venv to prove the environment is isolated:

    research/goldbot/.venv/Scripts/python research/goldbot/_isolation_check.py

It asserts two things:
  1. MetaTrader5 cannot be imported from this environment (no live-trading
     dependency leaked in). This passes only inside the research venv, which is
     exactly the point — the live bot's interpreter would fail this check.
  2. This file physically lives under research/goldbot, so the guard can only
     ever validate the quarantined tree.

On success it prints "ISOLATION OK" and exits 0.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def main() -> int:
    here = Path(__file__).resolve()
    as_posix = here.as_posix()
    assert "research/goldbot" in as_posix, (
        f"_isolation_check must live under research/goldbot; "
        f"resolved to {as_posix!r}"
    )

    spec = importlib.util.find_spec("MetaTrader5")
    assert spec is None, "MT5 present in research env — not isolated"

    print("ISOLATION OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
