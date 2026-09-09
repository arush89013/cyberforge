# ai_engine/train_model.py
# =========================================================
# Generates 5-dimensional synthetic behavioral data and
# trains an IsolationForest anomaly detection model.
#
# Features:
#   1. amount_norm     — normalised transaction amount (0–1)
#   2. location_risk   — IP anomaly score (0–1)
#   3. device_risk     — device trust score (0–1)
#   4. typing_norm     — normalised typing speed (0–1)
#   5. time_norm       — normalised hour of day (0–1)
# =========================================================

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
import pickle
import os


def generate_behavioral_data():
    """Generate synthetic normal + fraudulent transaction data."""
    np.random.seed(42)

    n_normal = 2500
    n_fraud = 400

    # ----- Normal transactions -----
    df_normal = pd.DataFrame({
        "amount_norm":   np.random.uniform(0.001, 0.08, n_normal),   # ₹100 – ₹8,000
        "location_risk": np.random.uniform(0.0, 0.25, n_normal),     # Known IPs
        "device_risk":   np.random.uniform(0.0, 0.25, n_normal),     # Known devices
        "typing_norm":   np.random.uniform(0.25, 0.65, n_normal),    # 2.5s – 6.5s normal
        "time_norm":     np.random.uniform(0.30, 0.87, n_normal),    # 7 AM – 8 PM
    })

    # ----- Fraudulent / anomalous transactions -----
    df_fraud = pd.DataFrame({
        "amount_norm":   np.random.uniform(0.20, 1.0, n_fraud),      # ₹20,000 – ₹100,000
        "location_risk": np.random.uniform(0.70, 1.0, n_fraud),      # Unknown IPs
        "device_risk":   np.random.uniform(0.70, 1.0, n_fraud),      # Unknown devices
        "typing_norm":   np.random.uniform(0.0, 0.12, n_fraud),      # Suspiciously fast
        "time_norm":     np.random.uniform(0.0, 0.22, n_fraud),      # Midnight – 5 AM
    })

    # ----- Medium-risk edge cases -----
    n_edge = 300
    df_edge = pd.DataFrame({
        "amount_norm":   np.random.uniform(0.10, 0.30, n_edge),
        "location_risk": np.random.uniform(0.30, 0.70, n_edge),
        "device_risk":   np.random.uniform(0.0, 0.50, n_edge),
        "typing_norm":   np.random.uniform(0.15, 0.80, n_edge),
        "time_norm":     np.random.uniform(0.0, 1.0, n_edge),
    })

    return pd.concat([df_normal, df_fraud, df_edge], ignore_index=True)


def train_and_save_model():
    """Train IsolationForest on 5-feature data and save the model."""
    df = generate_behavioral_data()
    features = ["amount_norm", "location_risk", "device_risk", "typing_norm", "time_norm"]

    model = IsolationForest(
        contamination=0.13,
        n_estimators=150,
        max_samples="auto",
        random_state=42,
    )
    model.fit(df[features])

    models_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
    os.makedirs(models_dir, exist_ok=True)

    model_path = os.path.join(models_dir, "risk_model.pkl")
    with open(model_path, "wb") as f:
        pickle.dump(model, f)

    print("[OK] 5D Behavioral Risk Model trained and saved!")
    print(f"   Features: {features}")
    print(f"   Samples : {len(df)} ({df.shape})")
    print(f"   Saved to: {model_path}")


if __name__ == "__main__":
    train_and_save_model()