"""Sovereign Spread & EMBI+ Risk Premium Analyzer.

Computes cross-country sovereign spreads (Brazil vs US), EMBI+ country risk
deductions, real yield differentials via Fisher inflation adjustments,
and term structure slopes.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
import numpy as np


@dataclass
class SovereignSpreadResult:
    """Quantitative spread and risk breakdown across curve maturities."""
    maturities: List[float]
    br_yields: List[float]
    us_yields: List[float]
    nominal_spreads_bps: List[float]
    embi_bps: float
    spread_ex_embi_bps: List[float]
    real_spreads_bps: Optional[List[float]]
    br_2y_10y_slope_bps: float
    us_2y_10y_slope_bps: float
    policy_spread_bps: float  # Selic vs Fed Funds


class SovereignSpreadAnalyzer:
    """Analyzes sovereign yield differentials, EMBI+ risk, and real carry."""

    def __init__(
        self,
        embi_bps: float = 334.0,
        selic_rate: float = 10.75,
        fed_funds_rate: float = 0.25,
        br_inflation_ipca: float = 10.54,
        us_inflation_cpi: float = 7.90
    ):
        self.embi_bps = float(embi_bps)
        self.selic_rate = float(selic_rate)
        self.fed_funds_rate = float(fed_funds_rate)
        self.br_inflation = float(br_inflation_ipca)
        self.us_inflation = float(us_inflation_cpi)

    def calculate_spreads(
        self,
        maturities: List[float],
        br_yields: List[float],
        us_yields: List[float]
    ) -> SovereignSpreadResult:
        """Compute full sovereign spread matrix across common tenors.

        Args:
            maturities: List of maturities in years (e.g. [0.25, 0.5, 1, 2, 3, 5, 10])
            br_yields: Brazil sovereign yields in % (e.g. 12.24, 12.93, ...)
            us_yields: US Treasury yields in % (e.g. 0.49, 0.87, ...)

        Returns:
            SovereignSpreadResult with detailed metrics.
        """
        m_arr = np.asarray(maturities, dtype=float)
        br_arr = np.asarray(br_yields, dtype=float)
        us_arr = np.asarray(us_yields, dtype=float)

        if len(br_arr) != len(us_arr) or len(br_arr) != len(m_arr):
            raise ValueError("Maturities, br_yields, and us_yields must have equal length.")

        # Nominal spread in basis points: (BR - US) * 100
        nominal_spreads_bps = (br_arr - us_arr) * 100.0

        # Spread ex-EMBI: nominal spread - EMBI (bps)
        # Or: BR yield - (EMBI in %) - US yield
        spread_ex_embi_bps = nominal_spreads_bps - self.embi_bps

        # Real rates via exact Fisher relation: (1 + y) / (1 + pi) - 1
        br_real = ((1.0 + br_arr / 100.0) / (1.0 + self.br_inflation / 100.0) - 1.0) * 100.0
        us_real = ((1.0 + us_arr / 100.0) / (1.0 + self.us_inflation / 100.0) - 1.0) * 100.0
        real_spreads_bps = (br_real - us_real) * 100.0

        # Term structure slopes: 10Y - 2Y
        # Find closest to 2Y and 10Y
        idx_2y = int(np.argmin(np.abs(m_arr - 2.0)))
        idx_10y = int(np.argmin(np.abs(m_arr - 10.0)))

        br_slope = (br_arr[idx_10y] - br_arr[idx_2y]) * 100.0
        us_slope = (us_arr[idx_10y] - us_arr[idx_2y]) * 100.0

        policy_spread = (self.selic_rate - self.fed_funds_rate) * 100.0

        return SovereignSpreadResult(
            maturities=m_arr.tolist(),
            br_yields=br_arr.tolist(),
            us_yields=us_arr.tolist(),
            nominal_spreads_bps=nominal_spreads_bps.tolist(),
            embi_bps=self.embi_bps,
            spread_ex_embi_bps=spread_ex_embi_bps.tolist(),
            real_spreads_bps=real_spreads_bps.tolist(),
            br_2y_10y_slope_bps=float(br_slope),
            us_2y_10y_slope_bps=float(us_slope),
            policy_spread_bps=float(policy_spread)
        )
