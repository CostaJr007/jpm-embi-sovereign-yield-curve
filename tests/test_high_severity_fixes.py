"""Regression tests for HIGH/CRITICAL fixes: DCF survival weighting + loader tenor alignment."""

import math

import numpy as np
import pytest

from sovereign_embi.models.credit_dcf import SovereignCreditDCFEngine
from sovereign_embi.models.sovereign_spread import SovereignSpreadAnalyzer
from sovereign_embi.connectors.excel_loader import SovereignDataLoader


def test_dcf_matches_manual_survival_weighted_calc():
    """DCF com hazard conhecido vs calculo manual.

    Pega os bugs: S=exp(-h*yr) com h variavel, dcf sem S, EL sem S_{t-1}.
    """
    recovery = 0.40
    lgd = 1.0 - recovery
    engine = SovereignCreditDCFEngine(
        recovery_rate=recovery, spread_decay_factor=1.0
    )  # spread plano -> h constante
    initial_bps = 600.0  # spread 0.06 -> h = 0.06/0.6 = 0.10
    r = 0.12
    years = 3

    res = engine.evaluate_term_structure(
        initial_embi_bps=initial_bps, discount_rate=r, years=years
    )

    h = (initial_bps / 10000.0) / lgd
    assert h == pytest.approx(0.10)
    s_prev = 1.0
    pv_expected = 0.0
    for i, p in enumerate(res.periods, start=1):
        t = float(i)
        s = s_prev * math.exp(-h * 1.0)
        df = 1.0 / ((1.0 + r) ** t)
        dcf = (initial_bps / 10000.0) * s * df
        el = s_prev * (1.0 - math.exp(-h * 1.0)) * lgd * 10000.0
        pv_expected += dcf

        assert p.survival_prob == pytest.approx(s, rel=1e-9), f"S_t ano {t}"
        assert p.discount_factor == pytest.approx(df, rel=1e-12)
        assert p.dcf_credit_spread == pytest.approx(dcf, rel=1e-9), f"dcf ano {t}"
        assert p.expected_loss_bps == pytest.approx(el, rel=1e-9), f"EL ano {t}"
        s_prev = s

    assert res.cumulative_present_value == pytest.approx(pv_expected, rel=1e-9)


def test_dcf_recursive_survival_with_decaying_spread():
    """Com spread variavel, S_t deve ser recursivo (nao exp(-h_t*t))."""
    engine = SovereignCreditDCFEngine(
        recovery_rate=0.40, spread_decay_factor=0.968  # comportamento legado
    )
    res = engine.evaluate_term_structure(
        initial_embi_bps=1000.0, discount_rate=0.10, years=3
    )
    lgd = 0.60
    s_prev = 1.0
    for p in res.periods:
        h = (p.projected_embi_bps / 10000.0) / lgd
        s = s_prev * math.exp(-h * 1.0)
        assert p.survival_prob == pytest.approx(s, rel=1e-9)
        el = s_prev * (1.0 - math.exp(-h)) * lgd * 10000.0
        assert p.expected_loss_bps == pytest.approx(el, rel=1e-9)
        s_prev = s
    # Sobrevivencia cai monotonicamente e DCF e menor que o nao-ponderado.
    assert res.periods[0].survival_prob > res.periods[1].survival_prob
    raw = sum(
        (p.projected_embi_bps / 10000.0) * p.discount_factor for p in res.periods
    )
    assert res.cumulative_present_value < raw


def test_loader_aligns_us_to_br_tenors():
    """generate_sample_dataset tem grades distintas; loader interpola US em BR."""
    ds = SovereignDataLoader.generate_sample_dataset()
    # Documenta a divergencia de origem (nao podem ser comparadas ponto a ponto).
    assert list(ds.br_maturities) != list(ds.us_maturities)

    m, br_y, us_y = SovereignDataLoader.aligned_for_spread(ds)
    assert len(m) == len(br_y) == len(us_y) == len(ds.br_maturities)
    assert m == pytest.approx(list(ds.br_maturities))
    assert br_y == pytest.approx(list(ds.br_yields))

    # Nos nos coincidentes, interpolacao reproduz o valor US exato.
    us_map = dict(zip(ds.us_maturities, ds.us_yields))
    for tenor, y_interp in zip(m, us_y):
        if tenor in us_map:
            assert y_interp == pytest.approx(us_map[tenor], rel=1e-12)
    # Tenor BR 0.75 (ausente em US) cai entre 0.50->0.871 e 1.0->1.268.
    i = list(m).index(0.75)
    assert us_y[i] == pytest.approx((0.871 + 1.268) / 2.0, rel=1e-9)

    # Resultado alinhado alimenta calculate_spreads sem erro de tamanho.
    analyzer = SovereignSpreadAnalyzer()
    out = analyzer.calculate_spreads(m, br_y, us_y)
    assert len(out.nominal_spreads_bps) == len(m)


def test_loader_alignment_validates_empty_curves():
    from sovereign_embi.connectors.excel_loader import SovereignDataset

    empty = SovereignDataset(
        br_maturities=[], br_yields=[],
        us_maturities=[1.0], us_yields=[2.0],
        embi_bps=334.0, selic_rate=10.75, fed_funds_rate=0.25,
        br_inflation_ipca=10.54, us_inflation_cpi=7.90,
        br_gdp_forecast=3.4, us_gdp_forecast=7.0,
    )
    with pytest.raises(ValueError):
        SovereignDataLoader.aligned_for_spread(empty)
