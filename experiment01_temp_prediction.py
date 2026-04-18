"""
実験①：隣接ノードの温度予測
物理AAS Phase 1 — pico-2, pico-3 から pico-1 の温度を予測

目的：
  3ノード間の相関構造が「予測可能性」として具体化されるか検証
  PHNN研究の基礎となる「異なる観測源の統合」の実証

方針：
  3種類のモデルを比較してベースラインと学習効果を明確化
    M0: 単純平均    pico-1 ≈ (pico-2 + pico-3) / 2
    M1: 線形回帰    pico-1 = a*T2 + b*T3 + c*H2 + d*H3 + e
    M2: MLP 4-8-1   非線形 + 湿度情報の活用
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
from sklearn.linear_model import LinearRegression
from sklearn.neural_network import MLPRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.preprocessing import StandardScaler

DATA_DIR = "data"
OUTPUT_DIR = "experiment01"
os.makedirs(OUTPUT_DIR, exist_ok=True)

EXPERIMENT_START = pd.Timestamp("2026-04-18 19:10:00")
EXPERIMENT_END = pd.Timestamp("2026-04-18 20:10:00")
TRAIN_RATIO = 2/3

print("=" * 70)
print("実験①: 隣接ノードの温度予測")
print("=" * 70)

sensor = pd.read_csv(os.path.join(DATA_DIR, "sensor_data.csv"))
sensor["timestamp"] = pd.to_datetime(sensor["timestamp"])

sensor = sensor[
    (sensor["timestamp"] >= EXPERIMENT_START)
    & (sensor["timestamp"] < EXPERIMENT_END)
].copy()

print(f"\n学習データ期間: {EXPERIMENT_START} 〜 {EXPERIMENT_END}")
print(f"総レコード数: {len(sensor)}")
print(f"ノード別: ")
print(sensor.groupby("node_id").size())

if len(sensor) < 100:
    print("\nデータ不足。もう少し待ってから実行してください。")
    exit(1)

sensor["time_bin"] = sensor["timestamp"].dt.round("5s")

pivot_temp = sensor.pivot_table(
    index="time_bin", columns="node_id",
    values="temperature", aggfunc="mean"
)
pivot_hum = sensor.pivot_table(
    index="time_bin", columns="node_id",
    values="humidity", aggfunc="mean"
)

combined = pd.concat(
    [pivot_temp.add_suffix("_temp"), pivot_hum.add_suffix("_hum")],
    axis=1
).dropna()

print(f"\n整列後のサンプル数: {len(combined)}")

X_cols = ["pico-2_temp", "pico-3_temp", "pico-2_hum", "pico-3_hum"]
y_col = "pico-1_temp"

if not all(c in combined.columns for c in X_cols + [y_col]):
    print(f"\n必要なカラムが揃っていません。")
    print(f"Available: {combined.columns.tolist()}")
    exit(1)

X = combined[X_cols].values
y = combined[y_col].values
timestamps = combined.index

split_idx = int(len(X) * TRAIN_RATIO)
X_train, X_test = X[:split_idx], X[split_idx:]
y_train, y_test = y[:split_idx], y[split_idx:]
ts_train, ts_test = timestamps[:split_idx], timestamps[split_idx:]

print(f"\n訓練サンプル数: {len(X_train)}")
print(f"検証サンプル数: {len(X_test)}")

print("\n" + "=" * 70)
print("M0: 単純平均 pico-1 ~ (pico-2 + pico-3) / 2")
print("=" * 70)

y_pred_m0 = (X_test[:, 0] + X_test[:, 1]) / 2
mae_m0 = mean_absolute_error(y_test, y_pred_m0)
rmse_m0 = np.sqrt(mean_squared_error(y_test, y_pred_m0))
print(f"MAE : {mae_m0:.3f} degC")
print(f"RMSE: {rmse_m0:.3f} degC")

print("\n" + "=" * 70)
print("M1: 線形回帰 pico-1 = a*T2 + b*T3 + c*H2 + d*H3 + e")
print("=" * 70)

m1 = LinearRegression()
m1.fit(X_train, y_train)
y_pred_m1 = m1.predict(X_test)
mae_m1 = mean_absolute_error(y_test, y_pred_m1)
rmse_m1 = np.sqrt(mean_squared_error(y_test, y_pred_m1))
print(f"係数: {dict(zip(X_cols, m1.coef_.round(4)))}")
print(f"切片: {m1.intercept_:.4f}")
print(f"MAE : {mae_m1:.3f} degC")
print(f"RMSE: {rmse_m1:.3f} degC")

print("\n" + "=" * 70)
print("M2: MLP (4-8-1) 非線形回帰")
print("=" * 70)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

m2 = MLPRegressor(
    hidden_layer_sizes=(8,),
    activation="tanh",
    solver="lbfgs",
    max_iter=2000,
    random_state=42,
)
m2.fit(X_train_scaled, y_train)
y_pred_m2 = m2.predict(X_test_scaled)
mae_m2 = mean_absolute_error(y_test, y_pred_m2)
rmse_m2 = np.sqrt(mean_squared_error(y_test, y_pred_m2))
print(f"MAE : {mae_m2:.3f} degC")
print(f"RMSE: {rmse_m2:.3f} degC")

print("\n" + "=" * 70)
print("モデル比較")
print("=" * 70)

results = pd.DataFrame({
    "Model": ["M0 (mean)", "M1 (linear)", "M2 (MLP)"],
    "MAE (degC)": [mae_m0, mae_m1, mae_m2],
    "RMSE (degC)": [rmse_m0, rmse_m1, rmse_m2],
})
print(results.to_string(index=False))

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

ax = axes[0, 0]
ax.plot(ts_test, y_test, label="Actual (pico-1)", color="black", linewidth=1.5)
ax.plot(ts_test, y_pred_m0, label=f"M0 mean (MAE={mae_m0:.3f})",
        alpha=0.7, linewidth=1)
ax.plot(ts_test, y_pred_m1, label=f"M1 linear (MAE={mae_m1:.3f})",
        alpha=0.7, linewidth=1)
ax.plot(ts_test, y_pred_m2, label=f"M2 MLP (MAE={mae_m2:.3f})",
        alpha=0.7, linewidth=1)
ax.set_ylabel("Temperature (degC)")
ax.set_xlabel("Time")
ax.set_title("Predicted vs actual (test period)")
ax.legend(fontsize=9)
ax.grid(True, alpha=0.3)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))

ax = axes[0, 1]
ax.scatter(y_test, y_pred_m0, s=15, alpha=0.4, label="M0", color="#3498db")
ax.scatter(y_test, y_pred_m1, s=15, alpha=0.4, label="M1", color="#e67e22")
ax.scatter(y_test, y_pred_m2, s=15, alpha=0.4, label="M2", color="#27ae60")
mn = min(y_test.min(), y_pred_m0.min(), y_pred_m1.min(), y_pred_m2.min())
mx = max(y_test.max(), y_pred_m0.max(), y_pred_m1.max(), y_pred_m2.max())
ax.plot([mn, mx], [mn, mx], "k--", alpha=0.5, label="y=x")
ax.set_xlabel("Actual (degC)")
ax.set_ylabel("Predicted (degC)")
ax.set_title("Predicted vs Actual")
ax.legend()
ax.grid(True, alpha=0.3)

ax = axes[1, 0]
ax.hist(y_test - y_pred_m0, bins=30, alpha=0.4,
        label=f"M0 (std={np.std(y_test-y_pred_m0):.3f})")
ax.hist(y_test - y_pred_m1, bins=30, alpha=0.4,
        label=f"M1 (std={np.std(y_test-y_pred_m1):.3f})")
ax.hist(y_test - y_pred_m2, bins=30, alpha=0.4,
        label=f"M2 (std={np.std(y_test-y_pred_m2):.3f})")
ax.axvline(0, color="black", linestyle="--", alpha=0.5)
ax.set_xlabel("Residual: actual - predicted (degC)")
ax.set_ylabel("Frequency")
ax.set_title("Error distribution")
ax.legend()
ax.grid(True, alpha=0.3)

ax = axes[1, 1]
x_pos = [0, 1, 2]
maes = [mae_m0, mae_m1, mae_m2]
rmses = [rmse_m0, rmse_m1, rmse_m2]
width = 0.35
ax.bar([p - width/2 for p in x_pos], maes, width,
       label="MAE", color="#3498db", alpha=0.8)
ax.bar([p + width/2 for p in x_pos], rmses, width,
       label="RMSE", color="#e67e22", alpha=0.8)
ax.set_xticks(x_pos)
ax.set_xticklabels(["M0 mean", "M1 linear", "M2 MLP"])
ax.set_ylabel("Error (degC)")
ax.set_title("Model comparison")
ax.legend()
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "01_prediction_results.png"), dpi=120)
plt.close()
print(f"\nSaved: {OUTPUT_DIR}/01_prediction_results.png")

results.to_csv(os.path.join(OUTPUT_DIR, "model_comparison.csv"), index=False)
print(f"Saved: {OUTPUT_DIR}/model_comparison.csv")

print("\n" + "=" * 70)
print("解釈")
print("=" * 70)

if mae_m2 < mae_m1 < mae_m0:
    print("\n- M2 (MLP) が最も精度が高い")
    print("- 非線形関係と湿度情報が予測に寄与")
    print("- PHNN の非線形観測モデルの正当性の一端")
elif mae_m1 < mae_m0:
    print("\n- M1 (線形) が M0 より良いが M2 は上回らない")
    print("- 単純平均では不十分、線形補正で十分")
    print("- ノード間のバイアスが一定の可能性")
else:
    print("\n- M0 (単純平均) でも十分")
    print("- 3ノードはほぼ等しい環境を観測している")

improvement = (mae_m0 - mae_m2) / mae_m0 * 100
print(f"\nM0 -> M2 の誤差削減: {improvement:.1f}%")

if mae_m2 < 0.2:
    print("\n結論: 実験成功")
    print("  隣接ノードから pico-1 を高精度で予測可能")
    print("  AAS の空間的補完の基盤が成立")
else:
    print("\n結論: 予測精度は限定的")
    print("  ノード間に独立した情報が存在")
    print("  これは AAS の価値（統合の意味）を示す")
