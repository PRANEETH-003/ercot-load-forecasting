#!/usr/bin/env python3
"""
Phase 2 - Day-ahead ERCOT system load forecast.

Design (agreed with Teja, 2026-10-22):
  - Train: 2025-01-01 to 2025-07-31. Test: August 2025 (the peak month, the hardest exam).
  - Features v1: load history + calendar ONLY. This dataset has no weather in it,
    and we say so - no pretending otherwise.
  - Leakage discipline: every feature for target hour t is built from data at least
    24 hours old (exactly what would be known when a day-ahead forecast is issued).
    Chronological split, no shuffling - shuffling time series is cheating.
  - The bar: persistence ("tomorrow = today"). August persistence RMSE was 2,679 MW.
    Beat it or the README says the model added nothing.

Run: python3 scripts/forecast.py
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from xgboost import XGBRegressor

DATA = "data/clean/ercot_load_2025_clean.csv"
CHART = "outputs/phase2_peak_week.png"

df = pd.read_csv(DATA, parse_dates=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

# ---------- Features ----------
# Lags: the load 1 day, 2 days and 1 week before the hour we are predicting.
df["lag_24"] = df["load_mw"].shift(24)
df["lag_48"] = df["load_mw"].shift(48)
df["lag_168"] = df["load_mw"].shift(168)
# Rolling mean of the 24 hours that ended 24 hours ago (known at issue time).
df["roll_mean_24"] = df["load_mw"].shift(24).rolling(24).mean()
# Calendar: all known in advance, so no leakage.
df["hour"] = df["timestamp"].dt.hour
df["dow"] = df["timestamp"].dt.dayofweek
df["doy"] = df["timestamp"].dt.dayofyear
df["month"] = df["timestamp"].dt.month
df["is_weekend"] = (df["dow"] >= 5).astype(int)

FEATURES = ["lag_24", "lag_48", "lag_168", "roll_mean_24",
            "hour", "dow", "doy", "month", "is_weekend"]

data = df.dropna(subset=FEATURES).copy()
train = data[(data["timestamp"] >= "2025-01-01") & (data["timestamp"] < "2025-08-01")]
test = data[(data["timestamp"] >= "2025-08-01") & (data["timestamp"] < "2025-09-01")]
print(f"Train rows: {len(train)} (Jan-Jul) | Test rows: {len(test)} (August)")

# ---------- Model ----------
model = XGBRegressor(
    n_estimators=600, max_depth=6, learning_rate=0.05,
    subsample=0.9, colsample_bytree=0.9, random_state=42, n_jobs=4,
)
model.fit(train[FEATURES], train["load_mw"])
test = test.assign(pred=model.predict(test[FEATURES]))


def score(actual, pred):
    err = actual - pred
    rmse = float(np.sqrt((err ** 2).mean()))
    mape = float((err.abs() / actual).mean() * 100)
    return rmse, mape


rows = []
for name, col in [("Persistence (tomorrow = today)", "lag_24"),
                  ("Seasonal-naive (last week)", "lag_168"),
                  ("XGBoost v1 (lags + calendar)", "pred")]:
    rmse, mape = score(test["load_mw"], test[col])
    rows.append((name, rmse, mape))

print("\nAugust 2025 - day-ahead forecast scores (lower is better):")
for name, rmse, mape in rows:
    print(f"  {name:38s} RMSE {rmse:8,.0f} MW | MAPE {mape:.2f}%")
base = rows[0][1]
print(f"\nModel vs persistence: {(1 - rows[2][1] / base) * 100:.1f}% lower RMSE")

print("\nFeature importance:")
for f, imp in sorted(zip(FEATURES, model.feature_importances_), key=lambda x: -x[1]):
    print(f"  {f:14s} {imp:.3f}")

# ---------- Chart: predicted vs actual for the peak week (Aug 15-21) ----------
week = test[(test["timestamp"] >= "2025-08-15") & (test["timestamp"] < "2025-08-22")]
plt.figure(figsize=(13, 4.5))
plt.plot(week["timestamp"], week["load_mw"] / 1000, label="Actual", lw=1.6, color="#1f6fb2")
plt.plot(week["timestamp"], week["pred"] / 1000, label="XGBoost day-ahead", lw=1.4, color="#d95f02")
plt.plot(week["timestamp"], week["lag_24"] / 1000, label="Persistence", lw=1.0, ls="--", color="grey")
plt.title("Day-ahead forecast vs actual - peak week, Aug 15-21 2025 (GW)")
plt.ylabel("GW")
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(CHART, dpi=150)
print(f"\nChart saved: {CHART}")
