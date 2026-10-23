# ERCOT Load Analysis & Day-Ahead Forecasting (2025)

An end-to-end analysis of a full year of Texas grid load: what drives ERCOT demand,
where it concentrates, and how well a machine learning model can forecast it a day
ahead — graded honestly against the naive baselines a forecaster has to beat.

**Data:** ERCOT official Hourly Load Archive (Native Load, 2025) — 8,760 hours of
system load plus 8 weather zones. Weather: Open-Meteo archive (ERA5 reanalysis),
hourly temperature and dew point for Dallas, Houston, Austin, and San Antonio.

## Findings

**1. ERCOT is a summer-peaking system, and the peak is an evening event.**
In 2025 load topped out at 83,679 MW on August 18 at 17:00; the top three hours of
the year were all that afternoon. August's average daily peak (~80,700 MW) ran about
31% above January's (~61,500 MW). The shape flips by season: summer weekdays peak at
17:00 (air temperature peaks mid-afternoon, but buildings have absorbed heat all day
and residential cooling switches on as people get home, on top of commercial load),
while winter weekdays peak at 07:00, when overnight cold meets heating systems
recovering buildings from night setback. On the peak day, load climbed ~28 GW (+50%)
from the 04:00 floor to the 17:00 peak — the daily ramp a forecaster has to predict.

**2. Two metros carry the peak — industry sets the level, weather sets the peak.**
At the August 18 peak hour, North Central (Dallas–Fort Worth, 26,582 MW) and Coast
(Houston, 22,349 MW) together were ~58% of system load; the top three zones were
~76%. Industrial load runs around the clock, so it sets a zone's base level — but it
cannot explain the peak: all three metro zones hit 97–98% of their own annual maxima
in the same hot hour. The control case is Far West (Permian oil and gas), which runs
at 98% of its evening level at 3 AM — pure industrial load has no weather shape.
Gulf humidity does show up in Houston's shape (3 AM load is 69% of the 5 PM level,
vs 61% for Dallas–Fort Worth): moist air adds latent cooling load and muggy nights
give less overnight relief.

**3. In summer, history is almost enough. In winter, weather is the whole game.**
See the forecast results below — the same model that beat the baseline comfortably
in August *loses to the naive baseline* in December until weather features are added.

## Day-ahead forecasting

Method: chronological train/test splits (no shuffling — time series are never
shuffled). Every feature for hour *t* is built from data at least 24 hours old,
exactly what is known when a day-ahead forecast is issued. Models are graded against
persistence ("tomorrow = today") and seasonal-naive ("tomorrow = same day last week").

**Test: August 2025** (train Jan–Jul) — the peak month

| Model | RMSE (MW) | MAPE |
|---|---|---|
| Seasonal-naive | 3,421 | 3.87% |
| Persistence | 2,679 | 3.26% |
| XGBoost — lags + calendar | 2,369 | 2.72% |
| XGBoost — + weather | **1,745** | **2.06%** |

**Test: December 2025** (train Jan–Oct) — the winter report card

| Model | RMSE (MW) | MAPE |
|---|---|---|
| Seasonal-naive | 4,766 | 7.35% |
| Persistence | 3,559 | 5.27% |
| XGBoost — lags + calendar | 3,660 | 5.26% |
| XGBoost — + weather | **2,631** | **4.07%** |

Adding weather cut August error by 26% over the history-only model, and in December
it was the difference between beating persistence by 26% and losing to it. In the
August model, system temperature was the second most important feature overall
(after yesterday's load); dew point added little on top of temperature, because in
a Texas summer the two move together.

## Honest caveats

- The weather model uses **observed** weather as a stand-in for the day-ahead
  weather *forecast* used in real operations. Forecasts are good but imperfect, so
  operational scores would be somewhat worse than shown here.
- One year of data = one realization of each season. A colder or milder December
  would grade differently.
- System load only; zone-level models and day-ahead *price* forecasting are the
  planned next steps (ERCOT DAM settlement point prices).

## Run it

```bash
pip install -r requirements.txt
python3 scripts/download_and_clean.py   # load data -> data/clean/
python3 scripts/forecast.py             # v1: August test, lags + calendar
python3 scripts/forecast_v2.py          # v2: August test, + weather (fetches & caches weather)
python3 scripts/forecast_winter.py      # v2: December test
```

## Repo layout

- `scripts/` — data cleaning and the three forecast runs
- `data/clean/` — cleaned hourly load, 8,760 rows, with the cleaning choices
  documented in the script (ERCOT hour-ending labels, DST edge hours; nothing invented)
- `outputs/` — findings notes, result tables, charts
