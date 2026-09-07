import pickle
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(current_dir, "models", "risk_model.pkl")

try:
    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)
except FileNotFoundError:
    model = None
    print("Warning: risk_model.pkl not found.")


def evaluate_risk(transaction_data: dict) -> dict:
    if model is None:
        return {"risk_score": 50.0, "flags": ["model_missing"]}

    amount = transaction_data.get("amount", 0.0)

    # ML predict returns 1 for normal, -1 for anomaly
    prediction = model.predict([[amount]])

    flags = []
    # Force extreme scores so the demo UI triggers perfectly!
    if prediction[0] == 1:
        # ML says it's normal
        normalized_risk = 20.0
    else:
        # ML caught the massive anomaly
        normalized_risk = 88.0
        flags.append("highly_anomalous_amount")

    return {
        "risk_score": float(normalized_risk),
        "anomaly_detected": bool(prediction[0] == -1),
        "flags": flags
    }