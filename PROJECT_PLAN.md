# ERCOT Grid Load & Price Analysis

A portfolio project analyzing real ISO market data: hourly system load and
day-ahead hub settlement prices for ERCOT (the Texas grid operator), built
with Python and pandas.

## Goal

Use ERCOT's own published data to answer three practical questions:

1. What does ERCOT load actually look like — daily/seasonal shapes, what
   drives the peaks, and when do price spikes happen?
2. How well can a simple model forecast day-ahead system load, honestly
   benchmarked against a persistence baseline?
3. What are the 3 findings a grid/energy analyst would put in a report?

The project deliberately uses the same kind of data an energy analyst at an
ISO, utility, or energy consultancy works with, and documents every data
quirk found along the way (DST days, hour-ending labels) instead of hiding
them.

## Data sources (verified working, Oct 22, 2026)

| Dataset | Source | Status |
|---|---|---|
| Hourly load by weather zone + ERCOT total, 2025 | ERCOT "Hourly Load Data Archives", https://www.ercot.com/gridinfo/load/load_hist — file `Native_Load_2025.zip`, downloaded from https://www.ercot.com/files/docs/2025/02/11/Native_Load_2025.zip | ✅ Downloaded and cleaned |
| Day-ahead settlement point prices (hubs & load zones), 2025 | ERCOT data product NP4-180-ER "Historical DAM Load Zone and Hub Prices", https://www.ercot.com/mp/data-products/data-product-details?id=NP4-180-ER — file `DAMLZHBSPP_2025` (MIS report type 13060, doc ID 1177667469) | ⚠️ Archive exists and is listed by ERCOT's MIS API, but the MIS file-download service returned HTTP 404 from this network on every attempt (list API works, downloads don't). The cleaning script tries the download automatically and, failing that, uses the file if it is downloaded manually into `data/raw/`. |

Both sources are public and need no account or API key.

## Cleaned data — what we actually have (from running the script)

Script: `scripts/download_and_clean.py` → output `data/clean/ercot_load_2025_clean.csv`

- **Rows:** 8,760 hourly records
- **Range:** 2025-01-01 00:00 → 2025-12-31 23:00 (local time, hour-beginning)
- **Columns:** `timestamp, load_mw, coast_mw, east_mw, fwest_mw, north_mw,
  ncent_mw, south_mw, scent_mw, west_mw` (MW; `load_mw` is the ERCOT total,
  the rest are ERCOT's 8 weather zones)
- **Missing values:** 0 NaN cells in the whole file
- **Load stats:** mean 55,734.4 MW · min 38,362.8 MW · peak 83,679.0 MW on
  2025-08-18 at hour beginning 17:00
- **Cleaning issues found (real, and worth explaining in an interview):**
  - ERCOT labels hours by the hour *ending*, and the last hour of each day
    is labeled "24:00", which is not a valid clock time — parsed manually
    as `timestamp = date + (hour_ending − 1) hours`.
  - Exactly **one duplicated timestamp**: 2025-11-02 01:00 (fall-back DST
    day — that local hour really happens twice).
  - Exactly **one missing hour**: 2025-03-09 02:00 (spring-forward DST day —
    that local hour never exists).
  - Net effect: 8,760 rows for the year; no data was invented to fill the
    DST gap.
- **Prices:** not yet in the clean data (see status above). Once
  `DAMLZHBSPP_2025` is in `data/raw/`, the same script writes
  `ercot_dam_hub_prices_2025_clean.csv` (HB_NORTH, HB_HOUSTON, HB_SOUTH,
  HB_WEST, HB_PAN in $/MWh) and a merged `ercot_load_price_2025_clean.csv`.

## The three phases

### Phase 1 — Clean + EDA (data foundation ✅ done; EDA next)
- [x] Download and clean hourly load (script above)
- [ ] Load-shape analysis: average day by season, weekday vs weekend,
      heat-wave weeks vs mild weeks
- [ ] Peak drivers: top 20 load hours of 2025 — what day/hour/weather-zone
      mix do they share? Which zones drive the system peak?
- [ ] Once prices are in: price-spike conditions — how often do hub prices
      exceed e.g. $100/MWh and $500/MWh, and what did load look like in
      those hours (spike = high load, or low renewable + moderate load?)
- Notebook: `notebooks/01_load_eda.ipynb`

### Phase 2 — Day-ahead load forecast vs persistence baseline
- Task: predict each day's 24 hourly loads using only data available the
  day before (the same setup as the earlier ASHRAE building project, now
  at ISO system level)
- Baseline: persistence (tomorrow = same hours yesterday / last week)
- Model: gradient boosting (XGBoost) with lag, rolling, calendar features
- Honest evaluation: RMSE and MAPE on a held-out test period, a leakage
  checklist (no future weather actuals, no same-day information), and an
  error breakdown for peak hours vs all hours
- Notebook: `notebooks/02_load_forecast.ipynb`

### Phase 3 — Communicate it like an analyst
- README with exactly 3 findings, each backed by one chart
- Charts: seasonal load shapes, peak-hour anatomy, forecast vs actual on
  the hardest week
- Resume bullet (fill in the real numbers after Phase 2), e.g.:
  "Built an ERCOT grid analytics project in Python/pandas on 8,760 hours
  of ISO load data (2025): cleaned ERCOT's native load archive (DST and
  hour-ending quirks), analyzed peak drivers across 8 weather zones, and
  benchmarked a day-ahead load forecast against a persistence baseline
  (RMSE __ vs __)."

## Folder layout

```
ercot-load-price-analysis/
├── PROJECT_PLAN.md
├── data/
│   ├── raw/    Native_Load_2025.zip / .xlsx (ERCOT originals)
│   └── clean/  ercot_load_2025_clean.csv
├── notebooks/  (Phase 1 & 2 notebooks go here)
└── scripts/
    └── download_and_clean.py
```
