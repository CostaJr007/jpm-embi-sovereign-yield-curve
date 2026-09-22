"""Unit tests for fixed income carry & roll-down engine."""

import pytest
from sovereign_embi.models.nelson_siegel import NelsonSiegelCurve
from sovereign_embi.models.carry_rolldown import CarryRollDownEngine
from sovereign_embi.models.credit_dcf import SovereignCreditDCFEngine


def test_carry_rolldown_metrics():
    curve = NelsonSiegelCurve()
    # Upward sloping curve
    curve.fit([0.25, 0.5, 1.0, 2.0, 5.0, 10.0], [8.0, 8.5, 9.0, 9.5, 10.0, 10.5])

    engine = CarryRollDownEngine(curve)
    metrics = engine.calculate_metrics(maturities=[2.0, 5.0], horizon_years=0.25, funding_rate=8.0)

    assert len(metrics) == 2
    for m in metrics:
        assert m.modified_duration > 0
        assert m.carry_return_bps > 0
        assert m.total_expected_return_bps != 0


def test_credit_dcf():
    engine = SovereignCreditDCFEngine(recovery_rate=0.40)
    res = engine.evaluate_term_structure(initial_embi_bps=300.0, discount_rate=0.10, years=3)

    assert res.recovery_rate == 0.40
    assert len(res.periods) == 3
    assert res.cumulative_present_value > 0.0

    # Survival probability should decrease over time
    assert res.periods[0].survival_prob > res.periods[1].survival_prob > res.periods[2].survival_prob
