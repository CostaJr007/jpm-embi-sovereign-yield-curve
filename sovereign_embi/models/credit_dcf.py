"""Sovereign Credit Risk & DCF Spread Valuation.

Models sovereign default intensities, cumulative survival probabilities,
and discounted cash flow (DCF) valuations for sovereign credit spreads
using recovery rate assumptions (e.g. 40% standard emerging market recovery).
"""

from dataclasses import dataclass
from typing import List, Optional
import numpy as np


@dataclass
class CreditDCFPeriod:
    """Projected credit spread cash flow and valuation for a single year."""
    year: int
    projected_embi_bps: float
    hazard_rate: float
    survival_prob: float
    discount_factor: float
    dcf_credit_spread: float
    expected_loss_bps: float


@dataclass
class CreditDCFResult:
    """Multi-year credit risk DCF valuation."""
    recovery_rate: float
    initial_embi_bps: float
    discount_rate: float
    periods: List[CreditDCFPeriod]
    cumulative_present_value: float


class SovereignCreditDCFEngine:
    """Discounts and evaluates sovereign credit risk over multi-year horizons."""

    def __init__(
        self,
        recovery_rate: float = 0.40,  # 40% standard sovereign recovery
        default_decay_factor: float = 0.968  # Annual decay factor from legacy sheet
    ):
        self.recovery_rate = recovery_rate
        self.decay_factor = default_decay_factor

    def evaluate_term_structure(
        self,
        initial_embi_bps: float = 334.0,
        discount_rate: float = 0.12,  # Discount yield (e.g. 12%)
        years: int = 5
    ) -> CreditDCFResult:
        """Compute multi-year sovereign credit DCF projection.

        Args:
            initial_embi_bps: Starting EMBI+ spread in basis points (e.g. 334.0)
            discount_rate: Base sovereign discount rate in decimal (e.g. 0.12)
            years: Projection horizon in years (default: 5)

        Returns:
            CreditDCFResult with period-by-period cash flows and total PV.
        """
        periods: List[CreditDCFPeriod] = []
        loss_given_default = 1.0 - self.recovery_rate
        cumulative_pv = 0.0

        current_embi = initial_embi_bps
        for yr in range(1, years + 1):
            # Implied hazard rate lambda = spread / (1 - R)
            spread_decimal = (current_embi / 10000.0)
            hazard_rate = spread_decimal / max(loss_given_default, 0.01)

            # Cumulative survival probability
            survival_prob = float(np.exp(-hazard_rate * yr))

            # Discount factor (1 + r)^(-t)
            df = float(1.0 / ((1.0 + discount_rate) ** yr))

            # DCF value of spread
            dcf_val = spread_decimal * df
            cumulative_pv += dcf_val

            # Expected loss
            default_prob_period = (1.0 - np.exp(-hazard_rate))
            expected_loss_bps = default_prob_period * loss_given_default * 10000.0

            periods.append(CreditDCFPeriod(
                year=yr,
                projected_embi_bps=float(current_embi),
                hazard_rate=float(hazard_rate),
                survival_prob=survival_prob,
                discount_factor=df,
                dcf_credit_spread=float(dcf_val),
                expected_loss_bps=float(expected_loss_bps)
            ))

            # Apply annual recovery/decay factor
            current_embi *= self.decay_factor

        return CreditDCFResult(
            recovery_rate=self.recovery_rate,
            initial_embi_bps=initial_embi_bps,
            discount_rate=discount_rate,
            periods=periods,
            cumulative_present_value=float(cumulative_pv)
        )
