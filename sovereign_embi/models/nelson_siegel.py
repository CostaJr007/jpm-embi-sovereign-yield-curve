"""Nelson-Siegel & Nelson-Siegel-Svensson Parametric Yield Curve Models.

Implements calibration, zero-coupon yield estimation, instantaneous forward rate
derivation, and discount factor extraction for sovereign bond curves.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple, Union
import numpy as np
from scipy.optimize import minimize


@dataclass
class NelsonSiegelParameters:
    """Estimated parameters of the Nelson-Siegel parametric curve."""
    beta0: float  # Long-term level factor (asymptotic yield)
    beta1: float  # Short-term slope factor
    beta2: float  # Medium-term curvature factor (hump / twist)
    tau: float    # Scale / decay parameter (location of maximum hump)
    rmse: float   # Root mean squared error of fit


@dataclass
class SvenssonParameters:
    """Estimated parameters of the Nelson-Siegel-Svensson parametric curve."""
    beta0: float
    beta1: float
    beta2: float
    beta3: float
    tau1: float
    tau2: float
    rmse: float


class NelsonSiegelCurve:
    """Nelson-Siegel (1987) yield curve model.

    Formula:
        y(m) = beta0 + beta1 * ((1 - exp(-m/tau)) / (m/tau))
                     + beta2 * (((1 - exp(-m/tau)) / (m/tau)) - exp(-m/tau))
    """

    def __init__(self, params: Optional[NelsonSiegelParameters] = None):
        self.params = params

    @staticmethod
    def zero_rate(
        maturities: np.ndarray,
        beta0: float,
        beta1: float,
        beta2: float,
        tau: float
    ) -> np.ndarray:
        """Calculate zero-coupon spot yields for given maturities in years."""
        m = np.maximum(np.asarray(maturities, dtype=float), 1e-6)
        m_tau = m / max(tau, 1e-6)
        factor1 = (1.0 - np.exp(-m_tau)) / m_tau
        factor2 = factor1 - np.exp(-m_tau)
        return beta0 + beta1 * factor1 + beta2 * factor2

    @staticmethod
    def instantaneous_forward_rate(
        maturities: np.ndarray,
        beta0: float,
        beta1: float,
        beta2: float,
        tau: float
    ) -> np.ndarray:
        """Calculate instantaneous forward rates f(m).

        f(m) = y(m) + m * y'(m)
             = beta0 + beta1 * exp(-m/tau) + beta2 * (m/tau) * exp(-m/tau)
        """
        m = np.maximum(np.asarray(maturities, dtype=float), 1e-6)
        m_tau = m / max(tau, 1e-6)
        exp_factor = np.exp(-m_tau)
        return beta0 + beta1 * exp_factor + beta2 * m_tau * exp_factor

    @staticmethod
    def discount_factor(
        maturities: np.ndarray,
        beta0: float,
        beta1: float,
        beta2: float,
        tau: float
    ) -> np.ndarray:
        """Calculate discount factor D(m) = exp(-y(m) * m). Yield must be decimal."""
        m = np.asarray(maturities, dtype=float)
        # Assuming yield in percentage (e.g., 12.5 means 12.5%), convert to decimal
        y = NelsonSiegelCurve.zero_rate(m, beta0, beta1, beta2, tau) / 100.0
        return np.exp(-y * m)

    def fit(
        self,
        maturities: Union[List[float], np.ndarray],
        yields: Union[List[float], np.ndarray]
    ) -> NelsonSiegelParameters:
        """Calibrate Nelson-Siegel parameters using nonlinear least squares.

        Args:
            maturities: Tenors in years (e.g. [0.25, 0.5, 1.0, 2.0, 5.0, 10.0])
            yields: Observed market yields (e.g. [12.24, 12.93, 13.49, 12.55, 12.28, 12.20])

        Returns:
            Calibrated NelsonSiegelParameters dataclass.
        """
        m = np.asarray(maturities, dtype=float)
        y = np.asarray(yields, dtype=float)

        if len(m) < 4:
            raise ValueError("At least 4 maturity/yield data points required for Nelson-Siegel calibration.")

        # Initial heuristics
        beta0_init = float(y[-1])
        beta1_init = float(y[0] - y[-1])
        beta2_init = float(2.0 * (np.mean(y) - 0.5 * (y[0] + y[-1])))
        tau_init = 1.5

        init_params = [beta0_init, beta1_init, beta2_init, tau_init]
        bounds = [(0.0, 50.0), (-30.0, 30.0), (-30.0, 30.0), (0.05, 20.0)]

        def objective(p):
            b0, b1, b2, t = p
            y_pred = self.zero_rate(m, b0, b1, b2, t)
            return np.sum((y - y_pred) ** 2)

        res = minimize(
            objective,
            x0=init_params,
            bounds=bounds,
            method="L-BFGS-B"
        )

        if not res.success:
            # Fallback to Nelder-Mead if L-BFGS-B struggles
            res = minimize(objective, x0=init_params, method="Nelder-Mead")

        b0, b1, b2, t = res.x
        fitted_yields = self.zero_rate(m, b0, b1, b2, t)
        rmse = float(np.sqrt(np.mean((y - fitted_yields) ** 2)))

        self.params = NelsonSiegelParameters(
            beta0=float(b0),
            beta1=float(b1),
            beta2=float(b2),
            tau=float(t),
            rmse=rmse
        )
        return self.params

    def predict(self, maturities: Union[List[float], np.ndarray]) -> np.ndarray:
        """Predict yields for given maturities using calibrated parameters."""
        if self.params is None:
            raise RuntimeError("Model has not been fitted yet. Call fit() first.")
        return self.zero_rate(
            np.asarray(maturities, dtype=float),
            self.params.beta0,
            self.params.beta1,
            self.params.beta2,
            self.params.tau
        )

    def forward_rates(self, maturities: Union[List[float], np.ndarray]) -> np.ndarray:
        """Predict instantaneous forward rates for given maturities."""
        if self.params is None:
            raise RuntimeError("Model has not been fitted yet. Call fit() first.")
        return self.instantaneous_forward_rate(
            np.asarray(maturities, dtype=float),
            self.params.beta0,
            self.params.beta1,
            self.params.beta2,
            self.params.tau
        )

    def discount_factors(self, maturities: Union[List[float], np.ndarray]) -> np.ndarray:
        """Predict discount factors for given maturities."""
        if self.params is None:
            raise RuntimeError("Model has not been fitted yet. Call fit() first.")
        return self.discount_factor(
            np.asarray(maturities, dtype=float),
            self.params.beta0,
            self.params.beta1,
            self.params.beta2,
            self.params.tau
        )
