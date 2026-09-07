import pickle
import os
import warnings

warnings.filterwarnings("ignore", category=UserWarning)

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "risk_model.pkl")

try:
    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)
except FileNotFoundError:
    model = None


def evaluate_risk(transaction_data: dict) -> dict:
    if model is None: return {"risk_score": 50.0, "flags": ["model_missing"]}

    amount = float(transaction_data.get("amount", 0.0))
    is_known_ip = transaction_data.get("is_known_ip", False)
    is_known_device = transaction_data.get("is_known_device", False)

    # Risk weights
    location_risk = 0.1 if is_known_ip else 0.85
    device_risk = 0.1 if is_known_device else 0.90

    raw_score = model.decision_function([[amount, location_risk, device_risk]])[0]
    base_risk = (0.15 - raw_score) * 200
    risk_score = max(5.0, min(95.0, base_risk))

    # ---------------------------------------------------------
    # TRUST BONUS: If the user device AND IP are recognized,
    # and the amount is safe, heavily reward them with trust!
    # ---------------------------------------------------------
    if is_known_ip and is_known_device and amount <= 10000:
        risk_score = 15.0  # Well below the 30-point OTP threshold!

    # Hard Bank Guardrails
    if amount >= 50000:
        risk_score = max(risk_score, 78.0)  # Forces ESP32
    elif amount >= 10000 and risk_score < 30:
        risk_score = max(risk_score, 45.0)  # Forces OTP for medium amounts

    flags = []
    if not is_known_device: flags.append("new_device")
    if not is_known_ip: flags.append("new_location")

    return {"risk_score": float(round(risk_score, 1)), "flags": flags}