"""Command-Line Interface for Sovereign Yield Curve & EMBI+ Risk Engine."""

import os
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from sovereign_embi.models.nelson_siegel import NelsonSiegelCurve
from sovereign_embi.models.sovereign_spread import SovereignSpreadAnalyzer
from sovereign_embi.models.carry_rolldown import CarryRollDownEngine
from sovereign_embi.models.credit_dcf import SovereignCreditDCFEngine
from sovereign_embi.connectors.excel_loader import SovereignDataLoader

app = typer.Typer(
    help="Sovereign Yield Curve & EMBI+ Risk Engine - Institutional Parametric Models and Sovereign Spread Analytics",
    add_completion=False
)
console = Console()


def _get_dataset(excel_path: Optional[str] = None):
    if excel_path and Path(excel_path).exists():
        return SovereignDataLoader.load_from_excel(excel_path)
    legacy = Path(__file__).parent.parent / "excel_legacy" / "sovereign_yield_curve_embi_legacy.xlsx"
    if legacy.exists():
        return SovereignDataLoader.load_from_excel(str(legacy))
    return SovereignDataLoader.generate_sample_dataset()


@app.command()
def fit(
    country: str = typer.Option("br", help="Country curve to fit ('br' or 'us')"),
    excel_path: Optional[str] = typer.Option(None, help="Path to Excel workbook")
):
    """Calibrate Nelson-Siegel parametric model on sovereign yield curve."""
    dataset = _get_dataset(excel_path)

    if country.lower() == "br":
        maturities = dataset.br_maturities
        yields = dataset.br_yields
        title = "Brazil Sovereign DI / Bond Curve (Nelson-Siegel Calibration)"
    else:
        maturities = dataset.us_maturities
        yields = dataset.us_yields
        title = "US Treasury Yield Curve (Nelson-Siegel Calibration)"

    curve = NelsonSiegelCurve()
    params = curve.fit(maturities, yields)

    console.print(Panel.fit(
        f"[bold cyan]{title}[/bold cyan]\n"
        f"[bold yellow]Level Factor (beta0):[/bold yellow] {params.beta0:.4f}%\n"
        f"[bold yellow]Slope Factor (beta1):[/bold yellow] {params.beta1:.4f}%\n"
        f"[bold yellow]Curvature (beta2):[/bold yellow]   {params.beta2:.4f}%\n"
        f"[bold yellow]Decay Scale (tau):[/bold yellow]     {params.tau:.4f} yrs\n"
        f"[bold green]Fitting RMSE:[/bold green]          {params.rmse:.4f}%",
        title="Parametric Model Results",
        border_style="green"
    ))

    table = Table(title="Curve Term Structure (Zero Rates, Forwards & Discount Factors)")
    table.add_column("Maturity (Yrs)", justify="right", style="cyan")
    table.add_column("Observed (%)", justify="right", style="magenta")
    table.add_column("Fitted Zero (%)", justify="right", style="yellow")
    table.add_column("Forward Rate (%)", justify="right", style="blue")
    table.add_column("Discount Factor", justify="right", style="green")

    fitted_zeros = curve.predict(maturities)
    forwards = curve.forward_rates(maturities)
    # Curva calibrada em percentual -> DF com units="percent".
    dfs = curve.discount_factors(maturities, units="percent")

    for m, y_obs, y_fit, fwd, df in zip(maturities, yields, fitted_zeros, forwards, dfs):
        table.add_row(
            f"{m:.2f}",
            f"{y_obs:.3f}%",
            f"{y_fit:.3f}%",
            f"{fwd:.3f}%",
            f"{df:.4f}"
        )

    console.print(table)


@app.command()
def spread(
    excel_path: Optional[str] = typer.Option(None, help="Path to Excel workbook")
):
    """Analyze sovereign yield differential, EMBI+ country risk deduction, and real spreads."""
    dataset = _get_dataset(excel_path)

    analyzer = SovereignSpreadAnalyzer(
        embi_bps=dataset.embi_bps,
        selic_rate=dataset.selic_rate,
        fed_funds_rate=dataset.fed_funds_rate,
        br_inflation_ipca=dataset.br_inflation_ipca,
        us_inflation_cpi=dataset.us_inflation_cpi
    )

    # Common maturities
    common_maturities = [0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0]

    curve_br = NelsonSiegelCurve()
    curve_br.fit(dataset.br_maturities, dataset.br_yields)

    curve_us = NelsonSiegelCurve()
    curve_us.fit(dataset.us_maturities, dataset.us_yields)

    br_y = curve_br.predict(common_maturities).tolist()
    us_y = curve_us.predict(common_maturities).tolist()

    res = analyzer.calculate_spreads(common_maturities, br_y, us_y)

    console.print(Panel.fit(
        f"[bold yellow]EMBI+ Brasil Risk Premium:[/bold yellow] [bold red]{res.embi_bps:.1f} bps[/bold red]\n"
        f"[bold yellow]Policy Spread (Selic - Fed Funds):[/bold yellow] [bold cyan]{res.policy_spread_bps:.1f} bps[/bold cyan]\n"
        f"[bold yellow]Brazil 2Y-10Y Curve Slope:[/bold yellow] [magenta]{res.br_2y_10y_slope_bps:.1f} bps[/magenta]\n"
        f"[bold yellow]US 2Y-10Y Curve Slope:[/bold yellow]     [magenta]{res.us_2y_10y_slope_bps:.1f} bps[/magenta]",
        title="Cross-Border Macro Risk Indicators",
        border_style="cyan"
    ))

    table = Table(title="Sovereign Spread & EMBI+ Risk Matrix")
    table.add_column("Tenor (Yrs)", justify="right", style="cyan")
    table.add_column("Brazil Yield (%)", justify="right", style="magenta")
    table.add_column("US Yield (%)", justify="right", style="blue")
    table.add_column("Nominal Spread (bps)", justify="right", style="yellow")
    table.add_column("Spread ex-EMBI (bps)", justify="right", style="green")
    table.add_column("Real Spread (bps)", justify="right", style="white")

    for i, m in enumerate(res.maturities):
        ex_embi = res.spread_ex_embi_bps[i]
        color = "green" if ex_embi > 0 else "red"
        table.add_row(
            f"{m:.2f}",
            f"{res.br_yields[i]:.3f}%",
            f"{res.us_yields[i]:.3f}%",
            f"{res.nominal_spreads_bps[i]:.1f}",
            f"[{color}]{ex_embi:.1f}[/{color}]",
            f"{res.real_spreads_bps[i]:.1f}"
        )

    console.print(table)


@app.command()
def carry(
    horizon: float = typer.Option(0.25, help="Holding period horizon in years (0.25 = 3M, 1.0 = 1Y)"),
    funding: Optional[float] = typer.Option(10.75, help="Funding rate in % (Selic or repo)")
):
    """Compute fixed income carry and roll-down analytics along the Brazil DI curve."""
    dataset = _get_dataset()
    curve = NelsonSiegelCurve()
    curve.fit(dataset.br_maturities, dataset.br_yields)

    engine = CarryRollDownEngine(curve)
    eval_tenors = [0.5, 0.75, 1.0, 2.0, 3.0, 5.0, 8.0, 10.0]
    metrics = engine.calculate_metrics(eval_tenors, horizon_years=horizon, funding_rate=funding)

    table = Table(title=f"Brazil Curve Carry & Roll-Down (Horizon: {horizon*12:.0f} Months, Funding: {funding}%)")
    table.add_column("Tenor (Yrs)", justify="right", style="cyan")
    table.add_column("Current Yield (%)", justify="right", style="magenta")
    table.add_column("Rolled Yield (%)", justify="right", style="blue")
    table.add_column("Mod. Duration", justify="right", style="white")
    table.add_column("Carry (bps)", justify="right", style="yellow")
    table.add_column("Roll-down (bps)", justify="right", style="green")
    table.add_column("Total Return (bps)", justify="right", style="bold green")
    table.add_column("Breakeven Shift (bps)", justify="right", style="red")

    for item in metrics:
        table.add_row(
            f"{item.maturity:.2f}",
            f"{item.current_yield:.3f}%",
            f"{item.rolled_yield:.3f}%",
            f"{item.modified_duration:.2f}",
            f"{item.carry_return_bps:.1f}",
            f"{item.rolldown_return_bps:.1f}",
            f"{item.total_expected_return_bps:.1f}",
            f"{item.breakeven_yield_shift_bps:.1f}"
        )

    console.print(table)


@app.command()
def dcf(
    embi_bps: float = typer.Option(334.0, help="Initial EMBI+ risk spread in bps"),
    recovery: float = typer.Option(0.40, help="Sovereign recovery rate (default 0.40 = 40%)"),
    discount: float = typer.Option(0.12, help="Discount rate (default 0.12 = 12%)"),
    years: int = typer.Option(5, help="Projection years")
):
    """Run sovereign credit DCF and hazard rate valuation."""
    engine = SovereignCreditDCFEngine(recovery_rate=recovery)
    res = engine.evaluate_term_structure(
        initial_embi_bps=embi_bps,
        discount_rate=discount,
        years=years
    )

    console.print(Panel.fit(
        f"[bold yellow]Initial EMBI Spread:[/bold yellow] {res.initial_embi_bps:.1f} bps\n"
        f"[bold yellow]Recovery Rate:[/bold yellow]        {res.recovery_rate*100:.1f}%\n"
        f"[bold yellow]Discount Yield Rate:[/bold yellow]  {res.discount_rate*100:.1f}%\n"
        f"[bold green]Cumulative Present Value:[/bold green] {res.cumulative_present_value:.4f}",
        title="Sovereign Credit DCF Results",
        border_style="green"
    ))

    table = Table(title="Sovereign Risk Cash Flows & Default Intensity")
    table.add_column("Year", justify="center", style="cyan")
    table.add_column("Proj. EMBI (bps)", justify="right", style="yellow")
    table.add_column("Hazard Rate lambda", justify="right", style="magenta")
    table.add_column("Survival Prob (%)", justify="right", style="green")
    table.add_column("Discount Factor", justify="right", style="white")
    table.add_column("DCF Value", justify="right", style="blue")
    table.add_column("Expected Loss (bps)", justify="right", style="red")

    for p in res.periods:
        table.add_row(
            str(p.year),
            f"{p.projected_embi_bps:.1f}",
            f"{p.hazard_rate:.4f}",
            f"{p.survival_prob*100:.2f}%",
            f"{p.discount_factor:.4f}",
            f"{p.dcf_credit_spread:.5f}",
            f"{p.expected_loss_bps:.1f}"
        )

    console.print(table)


if __name__ == "__main__":
    app()
