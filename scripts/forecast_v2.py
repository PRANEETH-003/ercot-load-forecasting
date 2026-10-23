#!/usr/bin/env python3
"""
Phase 2, v2 - Day-ahead ERCOT load forecast WITH weather.

What changed from v1: weather features from the free Open-Meteo archive
(ERA5 reanalysis) for the four metros behind the big zones:
  Dallas (North Central), Houston (Coast), Austin + San Antonio (South Central).
Variables: 2m temperature and dew point (dew point = the humidity variable
from our Phase 1 discussion).

Honesty note (also in the README): a real day-ahead forecast uses FORECAST
weather. We use OBSERVED weather as a stand-in for the day-ahead forecast.
Temperature forecasts a day out are good but not perfect, so v2 scores are
mildly optimistic versus operations. We say so rather than hiding it.

Same split as v1 (train Jan-Jul, test August), same baselines, same bar.
Weather is fetched once and cached to data/raw/weather_2025.csv.
"""
import json
import urllib.request
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from xgboost import XGBRegressor

LOAD = "data/clean/ercot_load_2025_clean.csv"
WEATHER_CACHE = "data/raw/weather_2025.csv"
CHART = "outputs/phase2_v2_peak_week.png"

CITIES = {  # name -> (lat, lon)
    "dallas": (32.78, -96.80),
    "houston": (29.76, -95.37),
    "austin": (30.27, -97.74),
    "sanantonio": (29.42, -98.49),
}


def fetch_weather():
    frames = []
    for city, (lat, lon) in CITIES.items():
        url = (
            "https://archive-api.open-meteo.com/v1/archive"
            f"?latitude={lat}&longitude={lon}"
            "&start_date=2025-01-01&end_date=2025-12-31"
            "&hourly=temperature_2m,dew_point_2m"
            "&timezone=America%2FChicago"
        )
        with urllib.request.urlopen(url, timeout=120) as r:
            payload = json.load(r)
        h = payload["hourly"]
        frames.append(pd.DataFrame({
            "timestamp": pd.to_datetime(h["time"]),
            f"temp_{city}": h["temperature_2m"],
            f"dew_{city}": h["dew_point_2m"],
        }))
    w = frames[0]
    for f in frames[1:]:
        w = w.merge(f, on="timestamp", how="outer")
    w.to_csv(WEATHER_CACHE, index=False)
    return w


try:
    weather = pd.read_csv(WEATHER_CACHE, parse_dates=["timestamp"])
    print(f"Weather loaded from cache: {len(weather)} rows")
except FileNotFoundError:
    weather = fetch_weather()
    print(f"Weather fetched from Open-Meteo: {len(weather)} rows")

# System-level weather: simple average across the four metros.
temp_cols = [f"temp_{c}" for c in CITIES]
dew_cols = [f"dew_{c}" for c in CITIES]
weather["temp_sys"] = weather[temp_cols].mean(axis=1)
weather["dew_sys"] = weather[dew_cols].mean(axis=1)

df = pd.read_csv(LOAD, parse_dates=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
df = df.merge(weather, on="timestamp", how="inner")
print(f"Merged load+weather rows: {len(df)} (DST edge hours may drop in the merge; no data invented)")

# ---------- Features ----------
df["lag_24"] = df["load_mw"].shift(24)
df["lag_48"] = df["load_mw"].shift(48)
df["lag_168"] = df["load_mw"].shift(168)
df["roll_mean_24"] = df["load_mw"].shift(24).rolling(24).mean()
df["hour"] = df["timestamp"].dt.hour
df["dow"] = df["timestamp"].dt.dayofweek
df["doy"] = df["timestamp"].dt.dayofyear
df["month"] = df["timestamp"].dt.month
df["is_weekend"] = (df["dow"] >= 5).astype(int)

V1 = ["lag_24", "lag_48", "lag_168", "roll_mean_24", "hour", "dow", "doy", "month", "is_weekend"]
WX = temp_cols + dew_cols + ["temp_sys", "dew_sys"]
V2 = V1 + WX

data = df.dropna(subset=V2).copy()
train = data[(data["timestamp"] >= "2025-01-01") & (data["timestamp"] < "2025-08-01")]
test = data[(data["timestamp"] >= "2025-08-01") & (data["timestamp"] < "2025-09-01")]
print(f"Train rows: {len(train)} | Test rows: {len(test)}")


def run(features, label):
    m = XGBRegressor(n_estimators=600, max_depth=6, learning_rate=0.05,
                     subsample=0.9, colsample_bytree=0.9, random_state=42, n_jobs=4)
    m.fit(train[features], train["load_mw"])
    pred = m.predict(test[features])
    err = test["load_mw"] - pred
    rmse = float(np.sqrt((err ** 2).mean()))
    mape = float((err.abs() / test["load_mw"]).mean() * 100)
    print(f"  {label:34s} RMSE {rmse:8,.0f} MW | MAPE {mape:.2f}%")
    return m, pred, rmse


def baseline(col):
    err = test["load_mw"] - test[col]
    return float(np.sqrt((err ** 2).mean())), float((err.abs() / test["load_mw"]).mean() * 100)


print("\nAugust 2025 - day-ahead scores (lower is better):")
rp, mp = baseline("lag_24")
rs, ms = baseline("lag_168")
print(f"  {'Persistence (the bar)':34s} RMSE {rp:8,.0f} MW | MAPE {mp:.2f}%")
print(f"  {'Seasonal-naive':34s} RMSE {rs:8,.0f} MW | MAPE {ms:.2f}%")
_, _, rmse_v1 = run(V1, "XGBoost v1 (lags + calendar)")
model2, pred2, rmse_v2 = run(V2, "XGBoost v2 (+ weather)")
print(f"\nWeather's contribution: v1 {rmse_v1:,.0f} -> v2 {rmse_v2:,.0f} "
      f"({(1 - rmse_v2 / rmse_v1) * 100:.1f}% lower RMSE than v1; "
      f"{(1 - rmse_v2 / rp) * 100:.1f}% lower than persistence)")

print("\nTop v2 features:")
for f, imp in sorted(zip(V2, model2.feature_importances_), key=lambda x: -x[1])[:10]:
    print(f"  {f:16s} {imp:.3f}")

week_mask = (test["timestamp"] >= "2025-08-15") & (test["timestamp"] < "2025-08-22")
wk = test[week_mask]
plt.figure(figsize=(13, 4.5))
plt.plot(wk["timestamp"], wk["load_mw"] / 1000, label="Actual", lw=1.6, color="#1f6fb2")
plt.plot(wk["timestamp"], pred2[week_mask.values] / 1000, label="XGBoost v2 (weather)", lw=1.4, color="#2ca25f")
plt.plot(wk["timestamp"], wk["lag_24"] / 1000, label="Persistence", lw=1.0, ls="--", color="grey")
plt.title("Day-ahead forecast v2 vs actual - peak week, Aug 15-21 2025 (GW)")
plt.ylabel("GW")
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(CHART, dpi=150)
print(f"\nChart saved: {CHART}")
