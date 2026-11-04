"""
Liquidity level dataclass + source Protocol.

`side` is ICT-style: BUYSIDE = buy stops rest ABOVE the level (i.e., level was a
prior high); SELLSIDE = sell stops rest BELOW the level (prior low).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, List
import pandas as pd


BUYSIDE = "buyside"    # resting stops above the level (level was a high)
SELLSIDE = "sellside"  # resting stops below the level (level was a low)


@dataclass
class LiquidityLevel:
    price: float
    side: str                # BUYSIDE / SELLSIDE
    source: str              # producer name, e.g. "PriorDayHigh"
    formed_at: datetime      # timezone-aware UTC
    swept: bool = False
    meta: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.side not in (BUYSIDE, SELLSIDE):
            raise ValueError(f"invalid side: {self.side}")
        if self.formed_at.tzinfo is None:
            raise ValueError("formed_at must be tz-aware")


class LiquiditySource(Protocol):
    """A liquidity-level source.

    Implementations MUST be look-ahead safe: they may only read bars/sessions
    that are fully completed at or before as_of_ts.
    """
    name: str

    def get_levels(
        self,
        df_completed: pd.DataFrame,
        as_of_ts: pd.Timestamp,
    ) -> List[LiquidityLevel]:
        ...
