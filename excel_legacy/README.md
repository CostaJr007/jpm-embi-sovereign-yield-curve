# Legacy Workbook Provenance

The original workbook (`EMBI DOS DEUSES ATUALIZANDO REAL TIME.xlsx`) was
**reverse-engineered and then removed from version control**. Binaries are
intentionally not shipped (clone bloat, third-party material). The audited logic
lives on as the Python engine in `sovereign_embi/`.

| Item | Detail |
|---|---|
| Original file | `EMBI DOS DEUSES ATUALIZANDO REAL TIME.xlsx` |
| Sanitized copy (removed) | `excel_legacy/sovereign_yield_curve_embi_legacy.xlsx` |
| Sheets | `comparativo de retorno` (BR DI `C3:C11`, US Treasury `C18:C25`, EMBI 334 bps in `W2:W3`, DCF block `AB:AK`, EMBI history `AN:AO`), `Planilha1` (fragile mirror), `Table 0 (2)` / `Table 0 (3)` (raw Investing.com scrapes) |
| Benchmark | EMBI+ = **J.P. Morgan Emerging Markets Bond Index Plus** (Brazil spread, bps) |

## What the workbook got wrong (fixed in Python)

- Subtracted a decimal EMBI spread from a relative return (`I = H - $W$3`) — dimensionally invalid; Python computes `spread_bps = (BR - US_interp) * 100` per tenor.
- Summed rates/returns across tenors; discounted at 169.5% p.a. (`AE8 = AT3`); treated a spread as a default probability; double-counted premium (mid-year + year-end mix).
- No Nelson-Siegel, no Fisher exact real yield, no `DF = exp(-y*m)` — all implemented and tested in Python (`nelson_siegel.py`, `sovereign_spread.py`, `carry_rolldown.py`, `credit_dcf.py` with survival weighting `S_t = S_{t-1}·exp(-h_t)`).

## Runtime note

`SovereignDataLoader.load_from_excel(path)` accepts any user-supplied workbook with a
`comparativo de retorno` sheet. Without a file, the CLI/API run on a bundled
synthetic BR/US dataset (US curve interpolated onto BR tenors). No legacy binary is
required to run or test this repo.
