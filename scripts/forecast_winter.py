#!/usr/bin/env python3
"""
Phase 2, winter report card - same models, opposite season.

August graded the model on the summer peak. This run asks whether it
survives winter: train Jan 1 - Oct 31, 2025, test on December 2025.
Same feature sets as forecast.py (v1) and forecast_v2.py (v2), same
baselines, same leakage discipline (every feature at least 24h old).
Weather comes from the cached Open-Meteo file built by forecast_v2.py.
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from xgboost import XGBRegressor

df = pd.read_csv("data/clean/ercot_load_2025_clean.csv", parse_dates=["timestamp"])
weather = pd.read_csv("data/raw/weather_2025.csv", parse_dates=["timestamp"])
temp_cols = [c for c in weather.columns if c.startswith("temp_")]
dew_cols = [c for c in weather.columns if c.startswith("dew_")]
weather["temp_sys"] = weather[temp_cols].mean(axis=1)
weather["dew_sys"] = weather[dew_cols].mean(axis=1)
df = df.merge(weather, on="timestamp", how="inner").sort_values("timestamp").reset_index(drop=True)

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
V2 = V1 + temp_cols + dew_cols + ["temp_sys", "dew_sys"]

data = df.dropna(subset=V2).copy()
train = data[(data["timestamp"] >= "2025-01-01") & (data["timestamp"] < "2025-11-01")]
test = data[(data["timestamp"] >= "2025-12-01") & (data["timestamp"] < "2026-01-01")]
print(f"Winter test - train rows: {len(train)} (Jan-Oct) | test rows: {len(test)} (December)")


def score(actual, pred):
    err = actual - pred
    return float(np.sqrt((err ** 2).mean())), float((err.abs() / actual).mean() * 100)


def fit_predict(feats):
    m = XGBRegressor(n_estimators=600, max_depth=6, learning_rate=0.05,
                     subsample=0.9, colsample_bytree=0.9, random_state=42, n_jobs=4)
    m.fit(train[feats], train["load_mw"])
    return m.predict(test[feats])


print("\nDecember 2025 - day-ahead scores (lower is better):")
p_rmse, p_mape = score(test["load_mw"], test["lag_24"])
s_rmse, s_mape = score(test["load_mw"], test["lag_168"])
print(f"  {'Persistence (the bar)':34s} RMSE {p_rmse:8,.0f} MW | MAPE {p_mape:.2f}%")
print(f"  {'Seasonal-naive':34s} RMSE {s_rmse:8,.0f} MW | MAPE {s_mape:.2f}%")

pred2 = None
for name, feats in [("XGBoost v1 (lags + calendar)", V1), ("XGBoost v2 (+ weather)", V2)]:
    pred = fit_predict(feats)
    rmse, mape = score(test["load_mw"], pred)
    print(f"  {name:34s} RMSE {rmse:8,.0f} MW | MAPE {mape:.2f}%")
    if name.startswith("XGBoost v2"):
        pred2 = pred
        print(f"\nWinter verdict: v2 beats persistence by {(1 - rmse / p_rmse) * 100:.1f}% "
              f"(August margin was 34.8%).")

wk_mask = (test["timestamp"] >= "2025-12-15") & (test["timestamp"] < "2025-12-22")
wk = test[wk_mask]
plt.figure(figsize=(13, 4.5))
plt.plot(wk["timestamp"], wk["load_mw"] / 1000, label="Actual", lw=1.6, color="#1f6fb2")
plt.plot(wk["timestamp"], pred2[wk_mask.values] / 1000, label="XGBoost v2 (weather)", lw=1.4, color="#2ca25f")
plt.plot(wk["timestamp"], wk["lag_24"] / 1000, label="Persistence", lw=1.0, ls="--", color="grey")
plt.title("Day-ahead forecast v2 vs actual - winter week, Dec 15-21 2025 (GW)")
plt.ylabel("GW")
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig("outputs/phase2_winter_week.png", dpi=150)
print("Chart saved: outputs/phase2_winter_week.png")
