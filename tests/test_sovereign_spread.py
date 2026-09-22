"""Unit tests for sovereign spread and EMBI+ analyzer."""

import pytest
from sovereign_embi.models.sovereign_spread import SovereignSpreadAnalyzer


def test_sovereign_spread_calculation():
    analyzer = SovereignSpreadAnalyzer(
        embi_bps=300.0,
        selic_rate=11.0,
        fed_funds_rate=1.0,
        br_inflation_ipca=10.0,
        us_inflation_cpi=5.0
    )

    maturities = [1.0, 2.0, 10.0]
    br_yields = [12.0, 12.5, 12.0]
    us_yields = [2.0, 2.5, 3.0]

    res = analyzer.calculate_spreads(maturities, br_yields, us_yields)

    # Nominal spread = (12 - 2) * 100 = 1000 bps
    assert pytest.approx(res.nominal_spreads_bps[0], 0.1) == 1000.0

    # Spread ex-EMBI = 1000 - 300 = 700 bps
    assert pytest.approx(res.spread_ex_embi_bps[0], 0.1) == 700.0

    # Policy spread = (11 - 1) * 100 = 1000 bps
    assert pytest.approx(res.policy_spread_bps, 0.1) == 1000.0

    # Brazil 2Y-10Y slope = (12.0 - 12.5) * 100 = -50 bps (inversion)
    assert pytest.approx(res.br_2y_10y_slope_bps, 0.1) == -50.0

    # US 2Y-10Y slope = (3.0 - 2.5) * 100 = +50 bps
    assert pytest.approx(res.us_2y_10y_slope_bps, 0.1) == 50.0
