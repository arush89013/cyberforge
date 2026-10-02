# ai_engine/train_model.py
# =========================================================
# CyberForge v3.0 — Advanced Synthetic Data Generator & 
# Isolation Forest Trainer
#
# Generates realistic multi-modal behavioral transaction
# data across 5 normalized features with distinct fraud
# archetypes (bot attacks, account takeover, credential
# stuffing, social engineering, mule accounts).
# =========================================================

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
import pickle
import os


def generate_behavioral_data():
    np.random.seed(42)

    # Sub-population 1: Daily small payments (coffee, groceries, transport)
    n_micro = 2000
    df_micro = pd.DataFrame({
        "amount_norm":   np.clip(np.random.beta(2, 20, n_micro), 0, 1),           # ₹50 – ₹3,000
        "location_risk": np.clip(np.random.beta(1.5, 15, n_micro), 0, 1),         # Very familiar IPs
        "device_risk":   np.clip(np.random.beta(1.5, 15, n_micro), 0, 1),         # Very familiar devices
        "typing_norm":   np.clip(np.random.normal(0.40, 0.10, n_micro), 0.1, 0.9), # 3-5 seconds
        "time_norm":     np.clip(np.random.normal(0.55, 0.12, n_micro), 0.1, 0.95),# 9 AM – 7 PM peak
    })

    # Sub-population 2: Monthly bills and rent (regular, moderate amounts)
    n_bills = 800
    df_bills = pd.DataFrame({
        "amount_norm":   np.clip(np.random.normal(0.10, 0.04, n_bills), 0.02, 0.3),# ₹5,000 – ₹25,000
        "location_risk": np.clip(np.random.beta(2, 12, n_bills), 0, 1),
        "device_risk":   np.clip(np.random.beta(2, 12, n_bills), 0, 1),
        "typing_norm":   np.clip(np.random.normal(0.45, 0.12, n_bills), 0.1, 0.9),
        "time_norm":     np.clip(np.random.normal(0.50, 0.15, n_bills), 0.1, 0.95),
    })

    # Sub-population 3: Occasional larger transfers (investments, purchases)
    n_large = 400
    df_large = pd.DataFrame({
        "amount_norm":   np.clip(np.random.normal(0.25, 0.10, n_large), 0.05, 0.5),
        "location_risk": np.clip(np.random.beta(2, 10, n_large), 0, 1),
        "device_risk":   np.clip(np.random.beta(2, 10, n_large), 0, 1),
        "typing_norm":   np.clip(np.random.normal(0.50, 0.15, n_large), 0.1, 0.9),
        "time_norm":     np.clip(np.random.normal(0.55, 0.18, n_large), 0.05, 0.95),
    })

    # ============================================================
    # FRAUD ARCHETYPE 1: Automated Bot Attack
    # Very fast typing, unknown device/IP, various amounts, odd hours
    # ============================================================
    n_bot = 200
    df_bot = pd.DataFrame({
        "amount_norm":   np.clip(np.random.uniform(0.05, 0.80, n_bot), 0, 1),
        "location_risk": np.clip(np.random.uniform(0.75, 1.0, n_bot), 0, 1),
        "device_risk":   np.clip(np.random.uniform(0.80, 1.0, n_bot), 0, 1),
        "typing_norm":   np.clip(np.random.uniform(0.0, 0.08, n_bot), 0, 1),  # < 800ms
        "time_norm":     np.clip(np.random.uniform(0.0, 0.25, n_bot), 0, 1),  # 12 AM – 6 AM
    })

    # ============================================================
    # FRAUD ARCHETYPE 2: Account Takeover (Credential Stuffing)
    # Known-ish device but huge amounts, slightly off typing
    # ============================================================
    n_ato = 150
    df_ato = pd.DataFrame({
        "amount_norm":   np.clip(np.random.uniform(0.40, 1.0, n_ato), 0, 1),  # Large amounts
        "location_risk": np.clip(np.random.uniform(0.60, 1.0, n_ato), 0, 1),  # Different IP
        "device_risk":   np.clip(np.random.uniform(0.30, 0.80, n_ato), 0, 1), # Mixed device trust
        "typing_norm":   np.clip(np.random.uniform(0.65, 0.95, n_ato), 0, 1), # Abnormally slow
        "time_norm":     np.clip(np.random.uniform(0.0, 0.30, n_ato), 0, 1),  # Off-hours
    })

    # ============================================================
    # FRAUD ARCHETYPE 3: Social Engineering / Mule Drain
    # Legit-looking device but draining balance, normal hours
    # ============================================================
    n_mule = 100
    df_mule = pd.DataFrame({
        "amount_norm":   np.clip(np.random.uniform(0.60, 0.95, n_mule), 0, 1),# Very large
        "location_risk": np.clip(np.random.uniform(0.0, 0.40, n_mule), 0, 1), # Known IP (victim's)
        "device_risk":   np.clip(np.random.uniform(0.0, 0.30, n_mule), 0, 1), # Known device
        "typing_norm":   np.clip(np.random.normal(0.35, 0.10, n_mule), 0.1, 0.7),  # Normal-ish
        "time_norm":     np.clip(np.random.normal(0.50, 0.15, n_mule), 0.1, 0.9),  # Daytime
    })

    n_edge = 350
    df_edge = pd.DataFrame({
        "amount_norm":   np.clip(np.random.uniform(0.08, 0.35, n_edge), 0, 1),
        "location_risk": np.clip(np.random.uniform(0.20, 0.65, n_edge), 0, 1),
        "device_risk":   np.clip(np.random.uniform(0.10, 0.55, n_edge), 0, 1),
        "typing_norm":   np.clip(np.random.uniform(0.12, 0.75, n_edge), 0, 1),
        "time_norm":     np.clip(np.random.uniform(0.0, 1.0, n_edge), 0, 1),
    })

    return pd.concat([
        df_micro, df_bills, df_large,
        df_bot, df_ato, df_mule,
        df_edge
    ], ignore_index=True)


def train_and_save_model():
    df = generate_behavioral_data()
    features = ["amount_norm", "location_risk", "device_risk", "typing_norm", "time_norm"]

    model = IsolationForest(
        contamination=0.11,     # ~11% fraud rate in synthetic data
        n_estimators=200,       # More trees for better accuracy
        max_samples=0.8,        # Subsample 80% per tree for diversity
        max_features=0.8,       # Use 80% of features per tree
        bootstrap=True,         # Bootstrap sampling
        random_state=42,
    )
    model.fit(df[features])

    # Validate the model
    predictions = model.predict(df[features])
    n_anomalies = sum(1 for p in predictions if p == -1)
    anomaly_rate = n_anomalies / len(df) * 100

    models_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
    os.makedirs(models_dir, exist_ok=True)

    model_path = os.path.join(models_dir, "risk_model.pkl")
    with open(model_path, "wb") as f:
        pickle.dump(model, f)

    print("=" * 60)
    print("  CyberForge AI Risk Model v3.0 — Training Complete")
    print("=" * 60)
    print(f"  Features        : {features}")
    print(f"  Total Samples   : {len(df)}")
    print(f"  Normal Samples  : {len(df) - n_anomalies}")
    print(f"  Anomaly Samples : {n_anomalies} ({anomaly_rate:.1f}%)")
    print(f"  Estimators      : 200")
    print(f"  Contamination   : 0.11")
    print(f"  Fraud Archetypes: Bot Attack, Account Takeover, Social Engineering")
    print(f"  Saved to        : {model_path}")
    print("=" * 60)


if __name__ == "__main__":
    train_and_save_model()