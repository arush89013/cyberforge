import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
import pickle
import os


def generate_mock_data(num_samples=1000):
    """Generates synthetic transaction data for initial training."""
    np.random.seed(42)

    # Normal transactions (Low amounts)
    normal_amounts = np.random.uniform(10, 5000, int(num_samples * 0.95))

    # Fraudulent transactions (Massive amounts)
    fraud_amounts = np.random.uniform(20000, 100000, int(num_samples * 0.05))

    all_amounts = np.concatenate([normal_amounts, fraud_amounts])

    df = pd.DataFrame({"amount": all_amounts})
    return df


def train_and_save_model():
    print("1. Generating synthetic transaction data...")
    df = generate_mock_data()

    print("2. Training Isolation Forest Anomaly Detector...")
    # Isolation Forest isolates anomalies (like unusually large transfers)
    model = IsolationForest(contamination=0.05, random_state=42)
    model.fit(df[['amount']])

    # Ensure the models directory exists
    current_dir = os.path.dirname(os.path.abspath(__file__))
    models_dir = os.path.join(current_dir, "models")
    os.makedirs(models_dir, exist_ok=True)

    model_path = os.path.join(models_dir, "risk_model.pkl")
    print(f"3. Saving trained model to {model_path}...")

    with open(model_path, "wb") as f:
        pickle.dump(model, f)

    print("✅ Training complete. The .pkl file is ready for the backend!")


if __name__ == "__main__":
    train_and_save_model()