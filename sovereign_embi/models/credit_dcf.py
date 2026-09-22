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
    """Discounts and evaluates sovereign credit risk over multi-year horizons.

    Hazard-implied pricing (reduced-form, per-period):

        h_t      = spread_t / LGD              (spread decimal / loss-given-default)
        S_t      = S_{t-1} * exp(-h_t * dt)    (recursive survival, S_0 = 1, dt = 1 ano)
        DF_t     = (1 + r) ** (-t)             (discrete discount factor)
        dcf_t    = spread_t * S_t * DF_t       (survival-weighted present value)
        EL_t     = S_{t-1} * (1 - exp(-h_t * dt)) * LGD * 10000  (bps)

    Args:
        recovery_rate: Sovereign recovery assumption (default 0.40 = 40%,
            standard EM sovereign recovery).
        spread_decay_factor: Explicit annual multiplicative decay applied to the
            projected EMBI spread (current_embi *= spread_decay_factor each year).
            Default 1.0 = sem decaimento ad-hoc; o hazard h_t e derivado
            puramente da curva de spread (spread_t / LGD).
            A planilha legada usava 0.968 (~-3.2% a.a. de compressao do spread).
            Passe spread_decay_factor=0.968 para reproduzir o comportamento legado.
            Mantido como parametro explicito e documentado (nao mais "magico").
    """

    def __init__(
        self,
        recovery_rate: float = 0.40,  # 40% standard sovereign recovery
        spread_decay_factor: float = 1.0,  # sem decaimento por padrao; legado usava 0.968
        default_decay_factor: Optional[float] = None,  # alias legado (deprecated)
    ):
        self.recovery_rate = recovery_rate
        if default_decay_factor is not None:
            # Retrocompatibilidade com o nome antigo do parametro.
            self.decay_factor = float(default_decay_factor)
        else:
            self.decay_factor = float(spread_decay_factor)
        # Alias publico com nome explicito.
        self.spread_decay_factor = self.decay_factor

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
        survival_prev = 1.0  # S_0 = 1 (sem default antes do horizonte)
        for yr in range(1, years + 1):
            # Implied hazard rate lambda = spread / (1 - R)
            spread_decimal = (current_embi / 10000.0)
            hazard_rate = spread_decimal / max(loss_given_default, 0.01)

            # Passo anual: deltat = 1 ano.
            dt = 1.0
            # Sobrevivencia recursiva: S_t = S_{t-1} * exp(-h_t * dt).
            # (Antes: exp(-h_t * yr), incorreto quando h varia por periodo.)
            survival_prob = survival_prev * float(np.exp(-hazard_rate * dt))

            # Discount factor (1 + r)^(-t)
            df = float(1.0 / ((1.0 + discount_rate) ** yr))

            # DCF ponderado por sobrevivencia: spread_t * S_t * DF_t.
            # (Antes: spread * DF, sem peso de sobrevivencia.)
            dcf_val = spread_decimal * survival_prob * df
            cumulative_pv += dcf_val

            # Perda esperada marginal: S_{t-1} * (1 - exp(-h_t*dt)) * LGD.
            # (Antes: sem o fator S_{t-1}.)
            default_prob_period = survival_prev * (1.0 - np.exp(-hazard_rate * dt))
            expected_loss_bps = default_prob_period * loss_given_default * 10000.0

            periods.append(CreditDCFPeriod(
                year=yr,
                projected_embi_bps=float(current_embi),
                hazard_rate=float(hazard_rate),
                survival_prob=float(survival_prob),
                discount_factor=df,
                dcf_credit_spread=float(dcf_val),
                expected_loss_bps=float(expected_loss_bps)
            ))

            survival_prev = float(survival_prob)
            # Decaimento anual explicito do spread projetado
            # (default 1.0 = sem decaimento; legado = 0.968).
            current_embi *= self.decay_factor

        return CreditDCFResult(
            recovery_rate=self.recovery_rate,
            initial_embi_bps=initial_embi_bps,
            discount_rate=discount_rate,
            periods=periods,
            cumulative_present_value=float(cumulative_pv)
        )
