# Exploratory analysis - ML Economic 1 (Ajey)

Panel: 142 months, 31 series, 2015-01 to 2026-10.

## Q1. Stationarity: ADF (H0 = unit root) vs KPSS (H0 = stationary)

Both tests must agree before a series is declared I(0) or I(1).

| column                  |   n |   adf_p |   kpss_p | verdict    |
|:------------------------|----:|--------:|---------:|:-----------|
| exports_growth_yoy      | 141 |   0.612 |    0.1   | ambiguous  |
| ppi_growth_yoy          | 140 |   0.069 |    0.1   | ambiguous  |
| blr                     | 138 |   0.342 |    0.065 | ambiguous  |
| myr_per_usd             | 141 |   0.005 |    0.029 | ambiguous  |
| imports_growth_yoy      | 141 |   0.445 |    0.1   | ambiguous  |
| u_rate                  | 140 |   0.504 |    0.1   | ambiguous  |
| cpi_div04_yoy           | 141 |   0.297 |    0.1   | ambiguous  |
| cpi_core_yoy            |  93 |   0.013 |    0.01  | ambiguous  |
| cpi_inflation_yoy       | 141 |   0.457 |    0.1   | ambiguous  |
| cpi_div01_yoy           | 141 |   0.424 |    0.1   | ambiguous  |
| cpi_inflation_mom       | 141 |   0     |    0.1   | stationary |
| ipi_growth_mom          | 139 |   0     |    0.1   | stationary |
| li_leading_diffusion    | 139 |   0     |    0.1   | stationary |
| ipi_growth_yoy          | 128 |   0.02  |    0.1   | stationary |
| li_lagging              | 139 |   0.96  |    0.01  | unit root  |
| li_coincident           | 139 |   0.907 |    0.01  | unit root  |
| li_leading              | 139 |   0.936 |    0.01  | unit root  |
| m3_rm_mil               | 138 |   0.997 |    0.01  | unit root  |
| m2_rm_mil               | 138 |   0.998 |    0.01  | unit root  |
| ipi_index_sa            | 140 |   0.959 |    0.01  | unit root  |
| fdr_1mo                 | 138 |   0.474 |    0.01  | unit root  |
| ipi_mining_index        | 140 |   0.593 |    0.01  | unit root  |
| ipi_manufacturing_index | 140 |   0.986 |    0.01  | unit root  |
| ipi_electricity_index   | 140 |   0.958 |    0.01  | unit root  |
| trade_balance_rm_mil    | 141 |   0.767 |    0.01  | unit root  |
| imports_rm_mil          | 141 |   0.997 |    0.01  | unit root  |
| exports_rm_mil          | 141 |   0.994 |    0.01  | unit root  |
| lf_employed             | 140 |   0.914 |    0.01  | unit root  |
| p_rate                  | 140 |   0.982 |    0.01  | unit root  |
| fdr_3mo                 | 138 |   0.409 |    0.01  | unit root  |
| ipi_index               | 140 |   0.979 |    0.01  | unit root  |

Verdict counts: {'unit root': 17, 'ambiguous': 10, 'stationary': 4}

## Q2. Structural breaks in the AR(2) dynamics of the target

| series             | break      |   n_before |   n_after |     F |      p | break_significant   |
|:-------------------|:-----------|-----------:|----------:|------:|-------:|:--------------------|
| ipi_growth_yoy     | 2020-03-01 |         48 |        78 | 0.268 | 0.8485 | False               |
| ipi_growth_yoy     | 2021-06-01 |         63 |        63 | 0.211 | 0.8886 | False               |
| exports_growth_yoy | 2020-03-01 |         60 |        79 | 2.5   | 0.0623 | False               |
| exports_growth_yoy | 2021-06-01 |         75 |        64 | 0.549 | 0.6496 | False               |
| cpi_inflation_yoy  | 2020-03-01 |         60 |        79 | 1.08  | 0.3599 | False               |
| cpi_inflation_yoy  | 2021-06-01 |         75 |        64 | 0.278 | 0.8413 | False               |

## Q3. Parameter stability (CUSUM) on the target AR(2)

CUSUM statistic = 0.967, p = 0.3070 (cannot reject stable parameters); Durbin-Watson = 1.90.

## Q4. Seasonality: is DOSM's SA series actually smoother?

| series         |   seasonal_spread_pct |   ljungbox_p_12 |    var |   sa_seasonal_spread_pct |   sa_var |
|:---------------|----------------------:|----------------:|-------:|-------------------------:|---------:|
| ipi_index      |                  9.65 |               0 | 185.48 |                     3.35 |   174.05 |
| ipi_growth_yoy |                 42.84 |               0 |  43.73 |                   nan    |   nan    |

## Q5. Collinear pairs (|r| >= 0.8) - drop one from each pair

| series_a                | series_b                |     r |
|:------------------------|:------------------------|------:|
| m2_rm_mil               | m3_rm_mil               | 1     |
| fdr_1mo                 | fdr_3mo                 | 0.998 |
| blr                     | opr                     | 0.996 |
| ipi_index               | ipi_manufacturing_index | 0.992 |
| m3_rm_mil               | li_lagging              | 0.991 |
| m2_rm_mil               | li_lagging              | 0.99  |
| lf_employed             | m2_rm_mil               | 0.989 |
| lf_employed             | m3_rm_mil               | 0.989 |
| lf_employed             | li_lagging              | 0.985 |
| ipi_index_sa            | li_coincident           | 0.98  |
| exports_rm_mil          | imports_rm_mil          | 0.979 |
| lf_employed             | li_coincident           | 0.977 |
| p_rate                  | lf_employed             | 0.973 |
| ipi_index_sa            | ipi_manufacturing_index | 0.968 |
| fdr_3mo                 | opr                     | 0.967 |
| p_rate                  | li_coincident           | 0.964 |
| ipi_index               | ipi_index_sa            | 0.962 |
| m3_rm_mil               | li_coincident           | 0.958 |
| blr                     | fdr_3mo                 | 0.958 |
| m2_rm_mil               | li_coincident           | 0.958 |
| li_coincident           | li_lagging              | 0.957 |
| fdr_1mo                 | opr                     | 0.956 |
| p_rate                  | m3_rm_mil               | 0.954 |
| p_rate                  | m2_rm_mil               | 0.953 |
| ipi_manufacturing_index | li_coincident           | 0.951 |
