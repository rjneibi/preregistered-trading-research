"""Quarantine guard for the labelsizing_core research artifact.

Run this *inside* the research venv to prove the environment is isolated:

    research/labelsizing_core/.venv/Scripts/python research/labelsizing_core/_isolation_check.py

It asserts two things:
  1. MetaTrader5 cannot be imported from this environment (no live-trading
     dependency leaked in). This passes only inside the research venv, which is
     exactly the point — the live bot's interpreter would fail this check.
  2. This file physically lives under research/labelsizing_core, so the guard
     can only ever validate the quarantined tree.

On success it prints "ISOLATION OK" and exits 0.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def main() -> int:
    # (2) Refuse to run from anywhere other than the quarantined tree.
    here = Path(__file__).resolve()
    as_posix = here.as_posix()
    assert "research/labelsizing_core" in as_posix, (
        f"_isolation_check must live under research/labelsizing_core; "
        f"resolved to {as_posix!r}"
    )

    # (1) The research env must NOT be able to see MetaTrader5.
    spec = importlib.util.find_spec("MetaTrader5")
    assert spec is None, "MT5 present in research env — not isolated"

    print("ISOLATION OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
