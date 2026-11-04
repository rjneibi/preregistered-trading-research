"""Locked global parameters for the labelsizing_core validation harness.

Every constant the pipeline depends on lives here in one frozen dataclass so the
labeler, CPCV splitter, calibrator and optimizer all read identical values.
Nothing in this module imports MetaTrader5 or touches a broker.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    """Immutable configuration shared across the whole artifact."""

    # --- horizon / entry geometry -------------------------------------------
    TIMEFRAME: str = "H1"
    TAU_MAX: int = 24            # label horizon in bars
    N_CONFIRM: int = 2           # follow-through bars; entry at Close[t+N_CONFIRM]

    # --- features ------------------------------------------------------------
    USE_HMM_REGIME: bool = True  # regime feature flag
    # longest feature lookback (bars); HMM rolling window is 63*24 = 1512
    L_FEATURE_MAX: int = 1512 if USE_HMM_REGIME else 100

    # --- CPCV ---------------------------------------------------------------
    N_GROUPS: int = 6            # CPCV groups (N)
    K_TEST: int = 2             # CPCV test groups (k) -> phi(6,2)=C(5,1)=5 paths
    EMBARGO: int = TAU_MAX       # serial-correlation embargo floor

    # --- barrier sizing ------------------------------------------------------
    K_TP_ATR: float = 2.0        # TP distance in ATR units at entry
    K_SL_ATR: float = 1.0        # SL distance in ATR units at entry

    # --- synthetic data ------------------------------------------------------
    N_SYNTH_BARS: int = 20000    # synthetic H1 bars

    # --- GPD tail model ------------------------------------------------------
    GPD_XI_CLAMP: float = 0.49
    GPD_MIN_EXCEEDANCES: int = 30
    GPD_FALLBACK_MULT: float = 1.5  # D_SL multiplier when too few exceedances

    # --- CVaR / portfolio limits --------------------------------------------
    CVAR_ALPHA: float = 0.95
    CVAR_LIMIT: float = 0.03
    MAX_EXPOSURE: float = 1.0
    MAX_TURNOVER: float = 0.5
    C_SPREAD: float = 0.0001
    C_COMM: float = 0.00005
    N_SCENARIOS: int = 2000

    # --- determinism ---------------------------------------------------------
    RANDOM_SEED: int = 42


# A single shared instance is convenient; the dataclass is frozen so it is safe.
CONFIG = Config()
