
import pickle
import os
import math
import warnings
from datetime import datetime, timezone

warnings.filterwarnings("ignore", category=UserWarning)

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "risk_model.pkl")

try:
    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)
except FileNotFoundError:
    model = None

WEIGHTS = {
    "location":           0.15,
    "device":             0.15,
    "typing":             0.12,
    "amount":             0.18,
    "time":               0.10,
    "velocity":           0.12,
    "recipient":          0.10,
    "balance_ratio":      0.08,
}

def _sigmoid(x: float, midpoint: float = 0.5, steepness: float = 10.0) -> float:
    try:
        return 1.0 / (1.0 + math.exp(-steepness * (x - midpoint)))
    except OverflowError:
        return 0.0 if x < midpoint else 1.0


def _location_score(is_known_ip: bool) -> float:
    return 0.05 if is_known_ip else 0.88


def _device_score(is_known_device: bool) -> float:
    return 0.05 if is_known_device else 0.92


def _typing_score(typing_speed_ms: float | None, avg_typing_speed_ms: float | None) -> float:
    if typing_speed_ms is None:
        return 0.45  # No data → mild caution

    # Hard bot detection: extremely fast input
    if typing_speed_ms < 500:
        return 0.98  # Near-certain automated/scripted input
    if typing_speed_ms < 800:
        return 0.88  # Very likely bot or copy-paste

    # No historical average yet → assess on absolute speed alone
    if avg_typing_speed_ms is None or avg_typing_speed_ms <= 0:
        # Use absolute speed heuristic with sigmoid
        # Typical human: 2000-8000ms, suspicious below 1200ms
        return _sigmoid(1200.0 / max(typing_speed_ms, 1), midpoint=0.6, steepness=8.0)

    # Compute ratio and use smooth sigmoid for anomaly detection
    ratio = typing_speed_ms / avg_typing_speed_ms

    if ratio < 0.2:
        return 0.95     # Extremely faster than usual → likely bot
    elif ratio < 1.0:
        # Faster than usual: smooth curve from 0.2x (high risk) to 1.0x (low risk)
        return _sigmoid(1.0 - ratio, midpoint=0.5, steepness=6.0) * 0.7
    elif ratio <= 2.0:
        return 0.08     # Within normal behavioral variance
    elif ratio <= 3.5:
        # Slower than usual: gradual increase
        return _sigmoid(ratio - 2.0, midpoint=0.75, steepness=4.0) * 0.6
    else:
        return 0.78     # Extremely slow → suspicious (possible credential sharing)


def _amount_score(amount: float, avg_amount: float | None) -> float:
    # Absolute thresholds (regulatory guardrails — these are sharp)
    if amount >= 100000:
        return 0.98
    if amount >= 75000:
        return 0.90

    if amount >= 65000:
        return 0.82

    # No history → assess on absolute amount with smooth curve
    if avg_amount is None or avg_amount <= 0:
        # Sigmoid centered at ₹15,000 for new users
        return _sigmoid(amount / 100000.0, midpoint=0.15, steepness=20.0)

    # Deviation from personal average — smooth sigmoid
    ratio = amount / avg_amount

    if ratio <= 1.0:
        return 0.05     # At or below their average → very safe
    elif ratio <= 2.0:
        # Mildly above average → gentle rise
        return _sigmoid(ratio - 1.0, midpoint=0.5, steepness=4.0) * 0.3
    elif ratio <= 5.0:
        # Notably above average → moderate concern
        return 0.3 + _sigmoid(ratio - 2.0, midpoint=1.5, steepness=2.0) * 0.4
    elif ratio <= 10.0:
        return 0.75 + (ratio - 5.0) / 50.0  # Gradually approaching critical
    else:
        return 0.92     # Extreme deviation


def _time_score(current_hour: int) -> float:
    # Center of safe window at hour 14 (2 PM), std dev ~5 hours
    center = 14.0
    std_dev = 5.0
    
    # Gaussian-like safety curve
    safety = math.exp(-0.5 * ((current_hour - center) / std_dev) ** 2)
    
    # Invert: high safety → low risk score
    risk = 1.0 - safety
    
    # Scale to [0.05, 0.88] range
    return 0.05 + risk * 0.83


def _velocity_score(tx_count_last_hour: int, tx_count_last_day: int) -> float:
    # Hourly velocity
    if tx_count_last_hour >= 6:
        hour_risk = 0.95    # Severe burst
    elif tx_count_last_hour >= 4:
        hour_risk = 0.80    # High velocity
    elif tx_count_last_hour >= 3:
        hour_risk = 0.55    # Elevated
    elif tx_count_last_hour >= 2:
        hour_risk = 0.25    # Slightly above normal
    else:
        hour_risk = 0.05    # Normal

    # Daily velocity
    if tx_count_last_day >= 15:
        day_risk = 0.90
    elif tx_count_last_day >= 10:
        day_risk = 0.65
    elif tx_count_last_day >= 6:
        day_risk = 0.35
    else:
        day_risk = 0.05

    # Combined: hourly bursts are more suspicious than daily volume
    return hour_risk * 0.7 + day_risk * 0.3


def _recipient_score(is_known_recipient: bool, recipient_tx_count: int) -> float:
    if not is_known_recipient:
        return 0.75     # Never sent to this person before
    
    # Trust increases with frequency (diminishing returns via log)
    trust = min(1.0, math.log2(recipient_tx_count + 1) / 4.0)
    return max(0.03, 0.75 - trust * 0.72)


def _balance_ratio_score(amount: float, balance: float) -> float:
    if balance <= 0:
        return 0.5  # Can't compute ratio
    
    ratio = amount / balance
    
    if ratio >= 0.9:
        return 0.95     # Draining 90%+ of account
    elif ratio >= 0.7:
        return 0.80     # Sending majority of balance
    elif ratio >= 0.5:
        return 0.60     # Half the balance
    elif ratio >= 0.3:
        return 0.35     # Significant chunk
    elif ratio >= 0.1:
        return 0.15     # Reasonable proportion
    else:
        return 0.05     # Small fraction of balance


def evaluate_risk(transaction_data: dict) -> dict:
    # Extract all inputs with safe defaults
    amount             = float(transaction_data.get("amount", 0.0))
    is_known_ip        = transaction_data.get("is_known_ip", False)
    is_known_device    = transaction_data.get("is_known_device", False)
    typing_speed_ms    = transaction_data.get("typing_speed_ms")
    avg_typing_speed   = transaction_data.get("avg_typing_speed")
    avg_amount         = transaction_data.get("avg_amount")
    current_hour       = transaction_data.get("current_hour", datetime.now(timezone.utc).hour)
    tx_count_last_hour = transaction_data.get("tx_count_last_hour", 0)
    tx_count_last_day  = transaction_data.get("tx_count_last_day", 0)
    is_known_recipient = transaction_data.get("is_known_recipient", False)
    recipient_tx_count = transaction_data.get("recipient_tx_count", 0)
    balance            = transaction_data.get("balance", 1000000.0)
    travel_speed_kmh   = transaction_data.get("travel_speed_kmh", 0.0)

    loc_s   = _location_score(is_known_ip)
    dev_s   = _device_score(is_known_device)
    typ_s   = _typing_score(typing_speed_ms, avg_typing_speed)
    amt_s   = _amount_score(amount, avg_amount)
    time_s  = _time_score(current_hour)
    vel_s   = _velocity_score(tx_count_last_hour, tx_count_last_day)
    rec_s   = _recipient_score(is_known_recipient, recipient_tx_count)
    bal_s   = _balance_ratio_score(amount, balance)

    sub_scores = {
        "location":       round(loc_s, 3),
        "device":         round(dev_s, 3),
        "typing":         round(typ_s, 3),
        "amount":         round(amt_s, 3),
        "time":           round(time_s, 3),
        "velocity":       round(vel_s, 3),
        "recipient":      round(rec_s, 3),
        "balance_ratio":  round(bal_s, 3),
    }

    raw_risk = 0.0
    for dim, weight in WEIGHTS.items():
        raw_risk += weight * sub_scores[dim]
    raw_risk *= 100

    if model is not None:
        location_risk = 0.1 if is_known_ip else 0.85
        device_risk   = 0.1 if is_known_device else 0.90
        typing_norm   = min((typing_speed_ms or 5000) / 10000.0, 1.0)
        amount_norm   = min(amount / 100000.0, 1.0)
        time_norm     = current_hour / 23.0

        try:
            prediction = model.predict([[amount_norm, location_risk, device_risk, typing_norm, time_norm]])[0]
            anomaly_score = model.decision_function([[amount_norm, location_risk, device_risk, typing_norm, time_norm]])[0]
            
            if prediction == -1:
                # Model flagged anomaly — scale penalty by confidence
                penalty = min(15.0, abs(anomaly_score) * 30.0)
                raw_risk += penalty
        except Exception:
            pass

    # ---------------------------------------------------------------
    # 4. Multi-factor combination amplifiers
    #    (correlated risks are more dangerous than isolated ones)
    # ---------------------------------------------------------------
    high_score_count = sum(1 for s in sub_scores.values() if s >= 0.6)
    
    if high_score_count >= 5:
        raw_risk += 15.0   # 5+ dimensions flagged → severe amplification
    elif high_score_count >= 4:
        raw_risk += 10.0   # 4 dimensions flagged → strong amplification
    elif high_score_count >= 3:
        raw_risk += 5.0    # 3 dimensions flagged → moderate amplification

    # Specific dangerous combinations
    if not is_known_device and not is_known_ip and not is_known_recipient:
        raw_risk += 8.0   # Triple unknown: new device + new IP + new recipient

    if not is_known_device and typing_speed_ms is not None and typing_speed_ms < 800:
        raw_risk += 12.0  # Bot on unknown device — strong attack signal

    if vel_s >= 0.5 and amt_s >= 0.5:
        raw_risk += 6.0   # Fast transaction bursts with high amounts

    if bal_s >= 0.6 and not is_known_recipient:
        raw_risk += 8.0   # Draining balance to unknown person

    if is_known_ip and is_known_device and is_known_recipient:
        # Fully familiar context
        if amt_s <= 0.2 and typ_s <= 0.2 and vel_s <= 0.2:
            raw_risk = min(raw_risk, 10.0)  # Maximum trust → well below PIN
        elif amt_s <= 0.4 and typ_s <= 0.4:
            raw_risk = min(raw_risk, 18.0)  # Strong trust → still PIN only
    
    elif is_known_ip and is_known_device:
        # Known device and location but new recipient
        if amt_s <= 0.3 and typ_s <= 0.3:
            raw_risk = min(raw_risk, 20.0)  # Trust the user's environment

    if travel_speed_kmh > 800:
        raw_risk = max(raw_risk, 95.0)  # Impossible Travel lockout

    if amount >= 65000:
        raw_risk = max(raw_risk, 80.0)      # Forces hardware auth

    if amount >= 25000 and not is_known_device:
        raw_risk = max(raw_risk, 45.0)      # Forces OTP for large + new device

    if not is_known_device and not is_known_ip and typ_s >= 0.55:
        raw_risk = max(raw_risk, 60.0)      # Triple suspicious → OTP minimum

    if bal_s >= 0.8:
        raw_risk = max(raw_risk, 50.0)      # Draining 80%+ balance → OTP minimum

    if tx_count_last_hour >= 5:
        raw_risk = max(raw_risk, 70.0)      # Severe burst → near hardware auth

    # Clamp final score
    risk_score = max(5.0, min(98.0, raw_risk))

    if risk_score < 25:
        risk_level = "LOW"
    elif risk_score < 50:
        risk_level = "MEDIUM"
    elif risk_score < 80:
        risk_level = "HIGH"
    else:
        risk_level = "CRITICAL"

    flags = []
    
    # Location flags
    if not is_known_ip:
        flags.append("new_location")

    if travel_speed_kmh > 800:
        flags.append("impossible_travel_detected")

    # Device flags
    if not is_known_device:
        flags.append("new_device")

    # Typing biometric flags
    if typing_speed_ms is not None:
        if typing_speed_ms < 500:
            flags.append("bot_speed_detected")
        elif typing_speed_ms < 800:
            flags.append("automated_input_suspected")
        elif typ_s >= 0.55:
            flags.append("unusual_typing_pattern")

    # Amount flags
    if amt_s >= 0.8:
        flags.append("extreme_amount")
    elif amt_s >= 0.55:
        flags.append("unusual_amount")

    # Time flags
    if time_s >= 0.65:
        flags.append("unusual_hour")

    # Velocity flags
    if vel_s >= 0.7:
        flags.append("rapid_burst_transactions")
    elif vel_s >= 0.4:
        flags.append("elevated_transaction_frequency")

    # Recipient flags
    if not is_known_recipient:
        flags.append("new_recipient")

    # Balance flags
    if bal_s >= 0.8:
        flags.append("account_drain_attempt")
    elif bal_s >= 0.5:
        flags.append("large_balance_proportion")

    # Multi-factor combination flags
    if high_score_count >= 4:
        flags.append("multi_factor_anomaly")

    # Confidence is higher when we have more historical data
    data_points = 0
    if avg_amount is not None:
        data_points += 1
    if avg_typing_speed is not None:
        data_points += 1
    if is_known_ip or is_known_device:
        data_points += 1
    if recipient_tx_count > 0:
        data_points += 1
    
    confidence = min(1.0, 0.4 + data_points * 0.15)

    return {
        "risk_score":  float(round(risk_score, 1)),
        "risk_level":  risk_level,
        "flags":       flags,
        "sub_scores":  sub_scores,
        "confidence":  round(confidence, 2),
    }