"""
CyberForge AI Risk Engine — Multi-Factor Behavioral Analysis
=============================================================
Evaluates 5 independent risk dimensions and produces a weighted
composite risk score (0–100).

Dimensions:
  1. Location anomaly   (25%)  — Is the IP new for this user?
  2. Device trust       (20%)  — Is the device fingerprint recognized?
  3. Typing biometrics  (15%)  — Is typing speed abnormal vs user average?
  4. Amount deviation   (25%)  — Is the amount unusual for this user?
  5. Time-of-day        (15%)  — Is the transaction at an unusual hour?
"""

import pickle
import os
import warnings
from datetime import datetime, timezone

warnings.filterwarnings("ignore", category=UserWarning)

# ---------------------------------------------------------------------------
# Load the IsolationForest model (secondary anomaly detector)
# ---------------------------------------------------------------------------
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "risk_model.pkl")

try:
    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)
except FileNotFoundError:
    model = None

# ---------------------------------------------------------------------------
# Configurable weights — must sum to 1.0
# ---------------------------------------------------------------------------
WEIGHTS = {
    "location": 0.25,
    "device":   0.20,
    "typing":   0.15,
    "amount":   0.25,
    "time":     0.15,
}


# ===================================================================
# Sub-score functions — each returns a float in [0.0, 1.0]
# ===================================================================

def _location_score(is_known_ip: bool) -> float:
    """IP-based location anomaly score."""
    if is_known_ip:
        return 0.1   # Familiar IP → very low risk
    return 0.9        # Completely new IP → high risk


def _device_score(is_known_device: bool) -> float:
    """Device fingerprint trust score."""
    if is_known_device:
        return 0.1   # Recognized device → very low risk
    return 0.95       # Unknown device → very high risk


def _typing_score(typing_speed_ms: float | None, avg_typing_speed_ms: float | None) -> float:
    """
    Typing speed biometric anomaly score.

    Compares the current session's typing speed (ms from first keystroke to
    submit) against the user's historical average.

    Red flags:
    - Abnormally fast (< 800ms or < 0.3× average) → likely bot / automated
    - Abnormally slow (> 3× average) → unfamiliar user or credential theft
    """
    # No data yet → neutral
    if typing_speed_ms is None:
        return 0.5

    # Hard bot detection: less than 800ms is almost certainly automated
    if typing_speed_ms < 800:
        return 0.95

    # No historical average yet → mild caution
    if avg_typing_speed_ms is None or avg_typing_speed_ms <= 0:
        return 0.4

    ratio = typing_speed_ms / avg_typing_speed_ms

    if ratio < 0.3:
        return 0.90     # Way too fast → bot-like
    elif ratio < 0.6:
        return 0.60     # Notably faster than usual
    elif ratio <= 1.8:
        return 0.10     # Within normal range
    elif ratio <= 3.0:
        return 0.55     # Notably slower
    else:
        return 0.80     # Extremely slow → suspicious


def _amount_score(amount: float, avg_amount: float | None) -> float:
    """
    Transaction amount anomaly score.

    Evaluates both absolute size and deviation from the user's historical
    average spending.
    """
    # Absolute thresholds
    if amount >= 100000:
        return 0.95
    if amount >= 50000:
        return 0.85

    # No history → base on absolute amount only
    if avg_amount is None or avg_amount <= 0:
        if amount >= 20000:
            return 0.60
        if amount >= 5000:
            return 0.35
        return 0.15

    # Deviation from personal average
    ratio = amount / avg_amount

    if ratio > 10:
        return 0.90     # 10× their average → extreme
    elif ratio > 5:
        return 0.75     # 5× their average → high
    elif ratio > 3:
        return 0.55     # 3× their average → elevated
    elif ratio > 1.5:
        return 0.30     # Slightly above average
    else:
        return 0.10     # Within normal spending


def _time_score(current_hour: int) -> float:
    """
    Time-of-day anomaly score.

    Transactions during late night / early morning (00:00 – 05:00) carry
    higher risk as most legitimate banking activity happens during day hours.
    """
    if 0 <= current_hour < 3:
        return 0.85     # Deep night → highest risk
    elif 3 <= current_hour < 5:
        return 0.70     # Very early morning → high risk
    elif 5 <= current_hour < 7:
        return 0.40     # Early morning → moderate
    elif 7 <= current_hour < 23:
        return 0.10     # Normal daytime hours → low risk
    else:  # 23:00
        return 0.50     # Late night → moderate


# ===================================================================
# Main evaluation function
# ===================================================================

def evaluate_risk(transaction_data: dict) -> dict:
    """
    Compute a composite risk score from 5 behavioral dimensions.

    Parameters (in transaction_data):
        amount            : float  — Transfer amount in ₹
        is_known_ip       : bool   — Has this user transacted from this IP before?
        is_known_device   : bool   — Has this user used this device before?
        typing_speed_ms   : float  — Milliseconds from first keystroke to submit
        avg_typing_speed  : float  — User's historical average typing speed
        avg_amount        : float  — User's historical average transaction amount
        current_hour      : int    — Hour of day (0-23) when transaction occurs

    Returns:
        {
            "risk_score": float,        # 0.0 – 100.0
            "flags": list[str],         # Human-readable risk flags
            "sub_scores": dict,         # Individual dimension scores
        }
    """
    amount           = float(transaction_data.get("amount", 0.0))
    is_known_ip      = transaction_data.get("is_known_ip", False)
    is_known_device  = transaction_data.get("is_known_device", False)
    typing_speed_ms  = transaction_data.get("typing_speed_ms")
    avg_typing_speed = transaction_data.get("avg_typing_speed")
    avg_amount       = transaction_data.get("avg_amount")
    current_hour     = transaction_data.get("current_hour", datetime.now(timezone.utc).hour)

    # ---------------------------------------------------------------
    # 1. Compute individual sub-scores
    # ---------------------------------------------------------------
    loc_s  = _location_score(is_known_ip)
    dev_s  = _device_score(is_known_device)
    typ_s  = _typing_score(typing_speed_ms, avg_typing_speed)
    amt_s  = _amount_score(amount, avg_amount)
    time_s = _time_score(current_hour)

    sub_scores = {
        "location": round(loc_s, 2),
        "device":   round(dev_s, 2),
        "typing":   round(typ_s, 2),
        "amount":   round(amt_s, 2),
        "time":     round(time_s, 2),
    }

    # ---------------------------------------------------------------
    # 2. Weighted ensemble → raw risk score (0–100)
    # ---------------------------------------------------------------
    raw_risk = (
        WEIGHTS["location"] * loc_s +
        WEIGHTS["device"]   * dev_s +
        WEIGHTS["typing"]   * typ_s +
        WEIGHTS["amount"]   * amt_s +
        WEIGHTS["time"]     * time_s
    ) * 100

    # ---------------------------------------------------------------
    # 3. IsolationForest secondary anomaly penalty
    # ---------------------------------------------------------------
    if model is not None:
        location_risk = 0.1 if is_known_ip else 0.85
        device_risk   = 0.1 if is_known_device else 0.90
        typing_norm   = min((typing_speed_ms or 5000) / 10000.0, 1.0)
        amount_norm   = min(amount / 100000.0, 1.0)
        time_norm     = current_hour / 23.0

        try:
            prediction = model.predict([[amount_norm, location_risk, device_risk, typing_norm, time_norm]])[0]
            if prediction == -1:
                # Model flagged as anomaly → add penalty
                raw_risk += 10
        except Exception:
            pass  # Model feature mismatch → skip (will be fixed after retraining)

    # ---------------------------------------------------------------
    # 4. Trust bonus — reward fully familiar behaviour
    # ---------------------------------------------------------------
    if is_known_ip and is_known_device and amount <= 10000:
        # Familiar user on trusted device and location with normal amount
        if typ_s <= 0.3:
            raw_risk = min(raw_risk, 12.0)  # Strong trust → well below PIN threshold

    # ---------------------------------------------------------------
    # 5. Hard bank guardrails (non-negotiable)
    # ---------------------------------------------------------------
    if amount >= 50000:
        raw_risk = max(raw_risk, 80.0)   # Forces hardware auth
    elif amount >= 10000 and not is_known_device:
        raw_risk = max(raw_risk, 40.0)   # Forces OTP for mid-amount + new device

    # Combined high-risk signals guardrail
    if not is_known_device and not is_known_ip and typ_s >= 0.55:
        raw_risk = max(raw_risk, 65.0)   # New device + new IP + suspicious typing

    # Clamp final score
    risk_score = max(5.0, min(95.0, raw_risk))

    # ---------------------------------------------------------------
    # 6. Build human-readable flags
    # ---------------------------------------------------------------
    flags = []
    if not is_known_ip:
        flags.append("new_location")
    if not is_known_device:
        flags.append("new_device")
    if typing_speed_ms is not None and typing_speed_ms < 800:
        flags.append("bot_speed_detected")
    elif typ_s >= 0.55:
        flags.append("unusual_typing_pattern")
    if amt_s >= 0.55:
        flags.append("unusual_amount")
    if time_s >= 0.50:
        flags.append("unusual_hour")

    return {
        "risk_score": float(round(risk_score, 1)),
        "flags": flags,
        "sub_scores": sub_scores,
    }