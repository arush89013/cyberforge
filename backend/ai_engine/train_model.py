# Inside ai_engine/train_model.py
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
import pickle
import os


def generate_behavioral_data():
    np.random.seed(42)
    # Normal: low amount, low location risk, low device risk
    df_normal = pd.DataFrame({
        "amount": np.random.uniform(10, 8000, 2000),
        "location_risk": np.random.uniform(0.0, 0.2, 2000),
        "device_risk": np.random.uniform(0.0, 0.2, 2000)
    })
    # Fraud: massive amount, high location risk, high device risk
    df_fraud = pd.DataFrame({
        "amount": np.random.uniform(20000, 100000, 300),
        "location_risk": np.random.uniform(0.8, 1.0, 300),
        "device_risk": np.random.uniform(0.8, 1.0, 300)
    })
    return pd.concat([df_normal, df_fraud], ignore_index=True)


def train_and_save_model():
    df = generate_behavioral_data()
    model = IsolationForest(contamination=0.15, random_state=42)
    model.fit(df[['amount', 'location_risk', 'device_risk']])

    models_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
    os.makedirs(models_dir, exist_ok=True)
    with open(os.path.join(models_dir, "risk_model.pkl"), "wb") as f:
        pickle.dump(model, f)
    print("✅ 3D Behavioral Model trained!")


if __name__ == "__main__":
    train_and_save_model()