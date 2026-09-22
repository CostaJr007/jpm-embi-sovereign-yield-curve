"""Unit tests for Nelson-Siegel parametric yield curve model."""

import numpy as np
from sovereign_embi.models.nelson_siegel import NelsonSiegelCurve


def test_nelson_siegel_limits():
    """Verify analytical boundary behavior of Nelson-Siegel model."""
    b0 = 12.0
    b1 = -2.0
    b2 = 4.0
    tau = 1.5

    # As m -> 0, y(0) -> beta0 + beta1
    y_short = NelsonSiegelCurve.zero_rate(np.array([1e-5]), b0, b1, b2, tau)[0]
    assert np.isclose(y_short, b0 + b1, atol=1e-3)

    # As m -> inf, y(inf) -> beta0
    y_long = NelsonSiegelCurve.zero_rate(np.array([10000.0]), b0, b1, b2, tau)[0]
    assert np.isclose(y_long, b0, atol=1e-3)

    # Forward rate f(0) -> beta0 + beta1
    f_short = NelsonSiegelCurve.instantaneous_forward_rate(np.array([1e-5]), b0, b1, b2, tau)[0]
    assert np.isclose(f_short, b0 + b1, atol=1e-3)

    # Forward rate f(inf) -> beta0
    f_long = NelsonSiegelCurve.instantaneous_forward_rate(np.array([10000.0]), b0, b1, b2, tau)[0]
    assert np.isclose(f_long, b0, atol=1e-3)


def test_nelson_siegel_fit():
    """Verify curve fitting optimization on synthetic curve."""
    maturities = [0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0]
    true_b0, true_b1, true_b2, true_tau = 11.5, -2.0, 5.0, 1.2
    synthetic_yields = NelsonSiegelCurve.zero_rate(
        np.array(maturities), true_b0, true_b1, true_b2, true_tau
    )

    curve = NelsonSiegelCurve()
    params = curve.fit(maturities, synthetic_yields)

    assert params.rmse < 0.05
    preds = curve.predict(maturities)
    assert np.allclose(preds, synthetic_yields, atol=0.05)


def test_discount_factors():
    """Verify discount factors D(m) = exp(-y*m) decrease monotonically and match mathematical definition."""
    maturities = [0.5, 1.0, 2.0, 5.0, 10.0]
    curve = NelsonSiegelCurve()
    curve.fit(maturities, [12.0, 12.5, 12.8, 12.6, 12.2])

    dfs = curve.discount_factors(maturities)
    preds = curve.predict(maturities)

    # Check bounds and exact formula invariant D(m) = exp(-y/100 * m)
    for m, y, df in zip(maturities, preds, dfs):
        expected_df = np.exp(-(y / 100.0) * m)
        assert np.isclose(df, expected_df, atol=1e-6)
        assert 0.0 < df < 1.0

    # Monotonicity check
    for i in range(len(dfs) - 1):
        assert dfs[i] > dfs[i + 1]
