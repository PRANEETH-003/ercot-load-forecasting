# Phase 2 Results — Day-Ahead ERCOT Load Forecast
Run 2026-10-22. Split agreed with Teja: train Jan 1 – Jul 31, 2025; test August 2025
(the peak month). Chronological split, no shuffling. All features for hour t use only
data at least 24 hours old (what is known when a day-ahead forecast is issued).

## August 2025 scores (lower is better)
| Model | RMSE (MW) | MAPE |
|---|---|---|
| Seasonal-naive (tomorrow = same day last week) | 3,421 | 3.87% |
| Persistence (tomorrow = today) — THE BAR | 2,679 | 3.26% |
| XGBoost v1 (lags 24/48/168 + rolling mean + calendar) | 2,369 | 2.72% |
| XGBoost v2 (v1 + weather) | 1,745 | 2.06% |

- v1 vs persistence: 11.6% lower RMSE
- v2 vs v1: 26.3% lower RMSE; v2 vs persistence: 34.8% lower RMSE

## v2 weather
Open-Meteo archive (ERA5), hourly temperature + dew point for Dallas, Houston, Austin,
San Antonio + their simple average (temp_sys / dew_sys). Cached: data/raw/weather_2025.csv.
Top v2 features: lag_24 (0.498), temp_sys (0.293), temp_dallas (0.051), is_weekend (0.045),
dew_dallas (0.020). Temperature was the #2 feature overall; dew point's marginal
contribution was modest (correlated with temperature in a Texas summer).

## Honest caveats (belong in the README)
1. v2 uses OBSERVED weather as a stand-in for the day-ahead weather FORECAST used in real
   operations. Operational scores would be somewhat worse than 1,745 MW.
2. One test month = one weather regime (summer peak). A winter test (train Jan–Oct, test
   December) has NOT been run yet — open item, Teja's call.
3. v1/v2 forecast system load only; zone-level models not attempted.

Scripts: scripts/forecast.py (v1), scripts/forecast_v2.py (v2).
Charts: outputs/phase2_peak_week.png, outputs/phase2_v2_peak_week.png.

## Winter report card (run 2026-10-22, scripts/forecast_winter.py)
Split: train Jan 1 – Oct 31, 2025; test December 2025. December is a harder month for
everyone (persistence RMSE 3,559 vs 2,679 in August — winter load is cold-snap driven).

| Model | RMSE (MW) | MAPE |
|---|---|---|
| Seasonal-naive | 4,766 | 7.35% |
| Persistence — THE BAR | 3,559 | 5.27% |
| XGBoost v1 (lags + calendar) | 3,660 | 5.26% |
| XGBoost v2 (+ weather) | 2,631 | 4.07% |

- **v1 FAILS the winter test** — worse than persistence. A lags-and-calendar model that
  beat the bar in August loses to "tomorrow = today" in December.
- **v2 beats persistence by 26.1%** in winter (34.8% in August). Weather is not a
  refinement; in winter it is the difference between beating the bar and losing to it.
Chart: outputs/phase2_winter_week.png.
