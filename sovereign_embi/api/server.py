"""FastAPI REST Service for Sovereign Yield Curves & EMBI+ Risk Engine."""

from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from sovereign_embi.models.nelson_siegel import NelsonSiegelCurve
from sovereign_embi.models.sovereign_spread import SovereignSpreadAnalyzer
from sovereign_embi.models.carry_rolldown import CarryRollDownEngine
from sovereign_embi.models.credit_dcf import SovereignCreditDCFEngine
from sovereign_embi.connectors.excel_loader import SovereignDataLoader

app = FastAPI(
    title="Sovereign Yield Curve & EMBI+ Spread Engine",
    description="Institutional parametric yield curve modeling (Nelson-Siegel), cross-border sovereign risk & EMBI+ spread analytics, carry & roll-down, and sovereign credit DCF valuation.",
    version="1.0.0"
)


class FitCurveRequest(BaseModel):
    maturities: List[float] = Field(..., json_schema_extra={"example": [0.25, 0.5, 1.0, 2.0, 5.0, 10.0]})
    yields: List[float] = Field(..., json_schema_extra={"example": [12.245, 12.939, 13.494, 12.556, 12.286, 12.207]})
    target_maturities: Optional[List[float]] = Field(default=None, json_schema_extra={"example": [0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 20.0, 30.0]})


class FitCurveResponse(BaseModel):
    beta0: float
    beta1: float
    beta2: float
    tau: float
    rmse: float
    interpolated_maturities: List[float]
    zero_rates: List[float]
    forward_rates: List[float]
    discount_factors: List[float]


class AnalyzeSpreadRequest(BaseModel):
    maturities: List[float] = Field(..., json_schema_extra={"example": [0.25, 0.5, 1.0, 2.0, 5.0, 10.0]})
    br_yields: List[float] = Field(..., json_schema_extra={"example": [12.245, 12.939, 13.494, 12.556, 12.286, 12.207]})
    us_yields: List[float] = Field(..., json_schema_extra={"example": [0.495, 0.871, 1.243, 1.860, 2.124, 2.169]})
    embi_bps: float = Field(default=334.0, json_schema_extra={"example": 334.0})
    selic_rate: float = Field(default=10.75, json_schema_extra={"example": 10.75})
    fed_funds_rate: float = Field(default=0.25, json_schema_extra={"example": 0.25})
    br_inflation_ipca: float = Field(default=10.54, json_schema_extra={"example": 10.54})
    us_inflation_cpi: float = Field(default=7.90, json_schema_extra={"example": 7.90})


class CarryRollDownRequest(BaseModel):
    maturities: List[float] = Field(..., json_schema_extra={"example": [0.25, 0.5, 1.0, 2.0, 5.0, 10.0]})
    yields: List[float] = Field(..., json_schema_extra={"example": [12.245, 12.939, 13.494, 12.556, 12.286, 12.207]})
    eval_maturities: Optional[List[float]] = Field(default=[1.0, 2.0, 3.0, 5.0, 10.0])
    horizon_years: float = Field(default=0.25, json_schema_extra={"example": 0.25})
    funding_rate: Optional[float] = Field(default=10.75, json_schema_extra={"example": 10.75})


class CreditDCFRequest(BaseModel):
    initial_embi_bps: float = Field(default=334.0, json_schema_extra={"example": 334.0})
    discount_rate: float = Field(default=0.12, json_schema_extra={"example": 0.12})
    recovery_rate: float = Field(default=0.40, json_schema_extra={"example": 0.40})
    years: int = Field(default=5, json_schema_extra={"example": 5})


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "sovereign-yield-curve-embi",
        "version": "1.0.0"
    }


@app.post("/fit-curve", response_model=FitCurveResponse)
def fit_curve(req: FitCurveRequest):
    try:
        curve = NelsonSiegelCurve()
        params = curve.fit(req.maturities, req.yields)
        targets = req.target_maturities or req.maturities
        zero_rates = curve.predict(targets).tolist()
        forwards = curve.forward_rates(targets).tolist()
        dfs = curve.discount_factors(targets).tolist()

        return FitCurveResponse(
            beta0=params.beta0,
            beta1=params.beta1,
            beta2=params.beta2,
            tau=params.tau,
            rmse=params.rmse,
            interpolated_maturities=targets,
            zero_rates=zero_rates,
            forward_rates=forwards,
            discount_factors=dfs
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/analyze-spread")
def analyze_spread(req: AnalyzeSpreadRequest):
    try:
        analyzer = SovereignSpreadAnalyzer(
            embi_bps=req.embi_bps,
            selic_rate=req.selic_rate,
            fed_funds_rate=req.fed_funds_rate,
            br_inflation_ipca=req.br_inflation_ipca,
            us_inflation_cpi=req.us_inflation_cpi
        )
        res = analyzer.calculate_spreads(req.maturities, req.br_yields, req.us_yields)
        return {
            "maturities": res.maturities,
            "br_yields": res.br_yields,
            "us_yields": res.us_yields,
            "nominal_spreads_bps": res.nominal_spreads_bps,
            "embi_bps": res.embi_bps,
            "spread_ex_embi_bps": res.spread_ex_embi_bps,
            "real_spreads_bps": res.real_spreads_bps,
            "br_2y_10y_slope_bps": res.br_2y_10y_slope_bps,
            "us_2y_10y_slope_bps": res.us_2y_10y_slope_bps,
            "policy_spread_bps": res.policy_spread_bps
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/carry-rolldown")
def carry_rolldown(req: CarryRollDownRequest):
    try:
        curve = NelsonSiegelCurve()
        curve.fit(req.maturities, req.yields)
        engine = CarryRollDownEngine(curve)
        items = engine.calculate_metrics(
            maturities=req.eval_maturities or [1.0, 2.0, 5.0, 10.0],
            horizon_years=req.horizon_years,
            funding_rate=req.funding_rate
        )
        return {"items": [item.__dict__ for item in items]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/credit-dcf")
def credit_dcf(req: CreditDCFRequest):
    try:
        engine = SovereignCreditDCFEngine(recovery_rate=req.recovery_rate)
        res = engine.evaluate_term_structure(
            initial_embi_bps=req.initial_embi_bps,
            discount_rate=req.discount_rate,
            years=req.years
        )
        return {
            "recovery_rate": res.recovery_rate,
            "initial_embi_bps": res.initial_embi_bps,
            "discount_rate": res.discount_rate,
            "cumulative_present_value": res.cumulative_present_value,
            "periods": [p.__dict__ for p in res.periods]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/macro-summary")
def macro_summary():
    """Returns real or baseline sovereign curves and macro differential summary."""
    try:
        import os
        legacy_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "excel_legacy", "EMBI_DOS_DEUSES_ATUALIZANDO_REAL_TIME.xlsx"
        )
        if os.path.exists(legacy_path):
            dataset = SovereignDataLoader.load_from_excel(legacy_path)
        else:
            dataset = SovereignDataLoader.generate_sample_dataset()

        return {
            "br_curve": dict(zip(dataset.br_maturities, dataset.br_yields)),
            "us_curve": dict(zip(dataset.us_maturities, dataset.us_yields)),
            "embi_bps": dataset.embi_bps,
            "selic_rate": dataset.selic_rate,
            "fed_funds_rate": dataset.fed_funds_rate,
            "policy_spread_bps": (dataset.selic_rate - dataset.fed_funds_rate) * 100.0,
            "br_inflation_ipca": dataset.br_inflation_ipca,
            "us_inflation_cpi": dataset.us_inflation_cpi,
            "inflation_differential_bps": (dataset.br_inflation_ipca - dataset.us_inflation_cpi) * 100.0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
