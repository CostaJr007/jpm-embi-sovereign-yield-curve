"""Fixed Income Carry & Roll-Down Analytics.

Calculates carry, roll-down return, modified duration, total expected horizon
return, and breakeven curve shifts under static yield curve assumptions.
"""

from dataclasses import dataclass
from typing import List, Optional
import numpy as np
from sovereign_embi.models.nelson_siegel import NelsonSiegelCurve


@dataclass
class CarryRollDownItem:
    """Carry and roll-down analytics for a single maturity."""
    maturity: float
    current_yield: float
    rolled_yield: float
    modified_duration: float
    carry_return_bps: float
    rolldown_return_bps: float
    total_expected_return_bps: float
    breakeven_yield_shift_bps: float


class CarryRollDownEngine:
    """Computes carry, roll-down, and breakeven metrics from fitted curves."""

    def __init__(self, curve: NelsonSiegelCurve):
        self.curve = curve

    def calculate_metrics(
        self,
        maturities: List[float],
        horizon_years: float = 0.25,  # 3-month horizon
        funding_rate: Optional[float] = None
    ) -> List[CarryRollDownItem]:
        """Compute carry, roll-down, and total expected return for given maturities.

        Args:
            maturities: List of bond maturities in years (e.g. [1.0, 2.0, 3.0, 5.0, 10.0])
            horizon_years: Holding period in years (0.25 for 3m, 1.0 for 1y)
            funding_rate: Short-term financing rate in % (optional)

        Returns:
            List of CarryRollDownItem metrics.
        """
        results = []
        for m in maturities:
            if m <= horizon_years:
                continue

            y_curr = float(self.curve.predict(np.array([m]))[0])
            m_rolled = m - horizon_years
            y_rolled = float(self.curve.predict(np.array([m_rolled]))[0])

            # Modified duration approximation for zero/par bond: D* = m / (1 + y)
            mod_dur = m / (1.0 + y_curr / 100.0)

            # Carry return: yield * horizon (or (yield - funding) * horizon)
            net_carry_rate = (y_curr - funding_rate) if funding_rate is not None else y_curr
            carry_bps = net_carry_rate * horizon_years * 100.0

            # Roll-down return: [y(m) - y(m - horizon)] * modified duration * 100
            # If curve is upward sloping, y(m) > y(rolled), yield drops -> price rises -> positive roll-down
            yield_change = (y_curr - y_rolled)
            rolldown_bps = yield_change * mod_dur * 100.0

            total_return_bps = carry_bps + rolldown_bps

            # Breakeven shift: total return / modified duration
            breakeven_shift_bps = (total_return_bps / mod_dur) if mod_dur > 0 else 0.0

            results.append(CarryRollDownItem(
                maturity=float(m),
                current_yield=y_curr,
                rolled_yield=y_rolled,
                modified_duration=float(mod_dur),
                carry_return_bps=float(carry_bps),
                rolldown_return_bps=float(rolldown_bps),
                total_expected_return_bps=float(total_return_bps),
                breakeven_yield_shift_bps=float(breakeven_shift_bps)
            ))

        return results
