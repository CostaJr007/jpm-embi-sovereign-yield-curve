# Sovereign Yield Curve & EMBI+ Risk Engine

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests: Pytest](https://img.shields.io/badge/Tests-10%20Passed-brightgreen.svg)](https://pytest.org)

Institutional Sovereign Fixed Income & Country Risk Engine. Reverse-engineered, formalized, and productionalized from macro trading spreadsheets (`EMBI DOS DEUSES ATUALIZANDO REAL TIME.xlsx`), modernizing legacy Excel query models into an asynchronous Python architecture featuring **Nelson-Siegel (1987)** parametric term-structure calibration, **EMBI+ sovereign risk spread decomposition**, **carry & roll-down dynamics**, and **multi-year credit risk DCF valuation**.

---

## Mathematical & Quantitative Foundations

### 1. Nelson-Siegel (1987) Parametric Curve Fitting
We model the zero-coupon spot yield curve $y(m)$ for maturity $m$ (in years) as a linear combination of decay factors:

$$y(m) = \beta_0 + \beta_1 \left( \frac{1 - e^{-m/\tau}}{m/\tau} \right) + \beta_2 \left( \frac{1 - e^{-m/\tau}}{m/\tau} - e^{-m/\tau} \right)$$

Where:
- $\beta_0$: **Long-term level factor** (asymptotic yield as $m \to \infty$).
- $\beta_1$: **Short-term slope factor** (as $m \to 0$, $y(0) = \beta_0 + \beta_1$).
- $\beta_2$: **Medium-term curvature factor** (governs hump or twist across the belly of the curve).
- $\tau$: **Scale/decay parameter** (determines the maturity where the curvature loading peaks).

From the fitted spot curve, we derive the **instantaneous forward rate** $f(m)$:

$$f(m) = y(m) + m \cdot y'(m) = \beta_0 + \beta_1 e^{-m/\tau} + \beta_2 \left(\frac{m}{\tau} e^{-m/\tau}\right)$$

And continuous **discount factors** $D(m)$:

$$D(m) = \exp\left(-\frac{y(m)}{100} \cdot m\right)$$

### 2. Cross-Country Sovereign Spread & EMBI+ Risk Decomposition
To assess relative value and carry trade attractiveness between Brazilian sovereign debt (DI / NTN-F) and US Treasuries:

- **Nominal Sovereign Spread**:
  $$S(m) = \left( y_{\text{BR}}(m) - y_{\text{US}}(m) \right) \times 100 \quad [\text{bps}]$$

- **EMBI+ Country Risk Deduction (Excess Spread)**:
  $$S_{\text{ex-EMBI}}(m) = S(m) - \text{EMBI}_{\text{bps}}$$
  *(Quantifies whether the cross-currency yield differential compensates investors above the J.P. Morgan EMBI+ Brazil sovereign default risk premium).*

- **Real Yield Differential via Fisher Equation**:
  $$r_{\text{real}}(m) = \frac{1 + y(m)/100}{1 + \pi^e/100} - 1$$
  $$\Delta r_{\text{real}}(m) = \left( r_{\text{BR, real}}(m) - r_{\text{US, real}}(m) \right) \times 10000 \quad [\text{bps}]$$

- **Curve Slopes & Monetary Policy Differentials**:
  - Slope ($10\text{Y} - 2\text{Y}$) to gauge inversion risks and term premia.
  - Policy Spread: $\text{Selic} - \text{Fed Funds}$.

### 3. Fixed Income Carry & Roll-Down Dynamics
For a bond of maturity $m$ held over horizon $\Delta t$ (e.g., 3 months = $0.25$ yrs) under a static yield curve assumption:

- **Carry Return**:
  $$\text{Carry} = \left( y(m) - \text{Funding Rate} \right) \cdot \Delta t \times 100 \quad [\text{bps}]$$

- **Modified Duration Approximation**:
  $$D^*(m) \approx \frac{m}{1 + y(m)/100}$$

- **Roll-Down Capital Gain**:
  $$\text{Roll-Down} = \left[ y(m) - y(m - \Delta t) \right] \cdot D^*(m) \times 100 \quad [\text{bps}]$$

- **Total Expected Return & Breakeven Yield Shift**:
  $$\text{Total Return} = \text{Carry} + \text{Roll-Down}$$
  $$\Delta y_{\text{breakeven}} = \frac{\text{Total Return}}{D^*(m)} \quad [\text{bps}]$$
  *(The upward yield shock required over horizon $\Delta t$ to completely eliminate carry and roll-down gains).*

### 4. Sovereign Credit Risk & Multi-Year DCF Valuation
Given sovereign risk spread $s = \text{EMBI}_{\text{bps}} / 10000$ and standard emerging market recovery rate $R = 40\%$:

- **Implied Hazard Rate (Default Intensity)**:
  $$\lambda = \frac{s}{1 - R}$$

- **Cumulative Survival Probability**:
  $$Q(t) = \exp(-\lambda t)$$

- **Discounted Cash Flow (DCF)**:
  $$\text{PV} = \sum_{t=1}^N \frac{s_t}{(1 + r_{\text{discount}})^t}$$

---

## Architecture & Project Layout

```
sovereign-yield-curve-embi/
├── sovereign_embi/
│   ├── models/
│   │   ├── nelson_siegel.py       # Parametric Nelson-Siegel curve calibration & forwards
│   │   ├── sovereign_spread.py    # Cross-border yield differential & EMBI+ deduction
│   │   ├── carry_rolldown.py      # Fixed income carry, roll-down, and breakeven shift
│   │   └── credit_dcf.py          # Sovereign credit hazard rates & multi-year DCF
│   ├── connectors/
│   │   └── excel_loader.py        # Excel parser for legacy workbook + fallback generator
│   ├── api/
│   │   └── server.py              # FastAPI microservice with Swagger OpenAPI specs
│   └── cli.py                     # Typer + Rich interactive terminal interface
├── excel_legacy/                  # Original Excel workbook reference
│   └── sovereign_yield_curve_embi_legacy.xlsx   # Sanitized legacy workbook (metadata stripped)
├── tests/
│   ├── test_nelson_siegel.py      # Analytical limits, RMSE fitting, and discount factors
│   ├── test_sovereign_spread.py   # Spreads, EMBI deductions, Fisher real rates
│   ├── test_carry_rolldown.py     # Carry, roll-down, and credit DCF assertions
│   └── test_api.py                # REST API endpoint tests
├── Dockerfile
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## Quick Start

### 1. Installation

```bash
git clone https://github.com/CostaJr007/sovereign-yield-curve-embi.git
cd sovereign-yield-curve-embi
pip install -r requirements.txt
```

### 2. Run Test Suite

```bash
python -m pytest tests/ -v
```

Expected output:
```
tests/test_api.py::test_health PASSED                                    [ 10%]
tests/test_api.py::test_fit_curve_endpoint PASSED                        [ 20%]
tests/test_api.py::test_analyze_spread_endpoint PASSED                   [ 30%]
tests/test_api.py::test_macro_summary_endpoint PASSED                    [ 40%]
tests/test_carry_rolldown.py::test_carry_rolldown_metrics PASSED         [ 50%]
tests/test_carry_rolldown.py::test_credit_dcf PASSED                     [ 60%]
tests/test_nelson_siegel.py::test_nelson_siegel_limits PASSED           [ 70%]
tests/test_nelson_siegel.py::test_nelson_siegel_fit PASSED              [ 80%]
tests/test_nelson_siegel.py::test_discount_factors PASSED               [ 90%]
tests/test_sovereign_spread.py::test_sovereign_spread_calculation PASSED [100%]
======= 10 passed in 1.10s =======
```

### 3. Interactive CLI Commands

#### Fit Nelson-Siegel Curve:
```bash
# Fit Brazil DI / Bond Curve
python -m sovereign_embi.cli fit --country br

# Fit US Treasury Curve
python -m sovereign_embi.cli fit --country us
```

#### Sovereign Spread & EMBI+ Risk Matrix:
```bash
python -m sovereign_embi.cli spread
```

#### Carry & Roll-Down Analytics:
```bash
python -m sovereign_embi.cli carry --horizon 0.25 --funding 10.75
```

#### Sovereign Credit DCF Valuation:
```bash
python -m sovereign_embi.cli dcf --embi-bps 334.0 --recovery 0.40 --years 5
```

### 4. Launch FastAPI REST Server

```bash
python -m uvicorn sovereign_embi.api.server:app --host 0.0.0.0 --port 8000 --reload
```

Interactive documentation is available at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

#### Example REST API Request:
```bash
curl -X POST "http://localhost:8000/fit-curve" \
     -H "Content-Type: application/json" \
     -d '{
       "maturities": [0.25, 0.5, 1.0, 2.0, 5.0, 10.0],
       "yields": [12.245, 12.939, 13.494, 12.556, 12.286, 12.207],
       "target_maturities": [1.0, 2.0, 5.0, 10.0]
     }'
```

---

## Docker Deployment

```bash
# Build Docker image
docker build -t sovereign-yield-curve-embi .

# Run containerized microservice
docker run -d -p 8000:8000 --name sovereign-embi sovereign-yield-curve-embi
```

---

## License
MIT License. Developed by Adeilson Costa ([CostaJr007](https://github.com/CostaJr007)).
