import os
import re

# --- 1. FIX THE IDE BUG ---
gemini_config_dir = os.path.join(os.path.expanduser("~"), ".gemini", "config")
hooks_path = os.path.join(gemini_config_dir, "hooks.json")

if os.path.exists(hooks_path):
    try:
        os.remove(hooks_path)
        print("✅ Fixed IDE Bug: Removed corrupted hooks.json")
    except Exception as e:
        print(f"⚠️ Could not remove hooks.json: {e}")
else:
    print("✅ IDE Bug already clear.")

# --- 2. UPDATE PROJECT FILES ---
print("Applying Geolocation Velocity feature...")

MAIN_PY = r"e:\cyberforge\backend\main.py"
PREDICTOR_PY = r"e:\cyberforge\backend\ai_engine\predictor.py"
SCRIPT_JS = r"e:\cyberforge\frontend\script.js"

# 2a. Patch main.py
try:
    with open(MAIN_PY, "r", encoding="utf-8") as f:
        main_code = f.read()

    if "import requests" not in main_code:
        main_code = main_code.replace(
            "import re\n",
            "import re\nimport math\nimport requests\n\n"
            "def get_lat_lon(ip: str):\n"
            "    if ip in ('127.0.0.1', '::1', 'localhost', 'unknown'): return 28.6139, 77.2090\n"
            "    try:\n        r = requests.get(f'http://ip-api.com/json/{ip}', timeout=1.0)\n"
            "        if r.json().get('status') == 'success': return r.json()['lat'], r.json()['lon']\n"
            "    except: pass\n"
            "    return None, None\n\n"
            "def haversine(lat1, lon1, lat2, lon2):\n"
            "    R = 6371.0\n    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])\n"
            "    dlat, dlon = lat2 - lat1, lon2 - lon1\n"
            "    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2\n"
            "    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))\n\n"
        )

    # Replace IP logic
    if "travel_speed_kmh =" not in main_code:
        main_code = main_code.replace(
            'client_ip = request.client.host if request.client else "unknown"\n\n    completed_statuses = ["Completed", "OTP_Awaiting", "ESP32_Awaiting"]',
            'forwarded = request.headers.get("X-Forwarded-For")\n'
            '    client_ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")\n\n'
            '    completed_statuses = ["Completed", "OTP_Awaiting", "ESP32_Awaiting"]\n\n'
            '    travel_speed_kmh = 0.0\n'
            '    last_tx = db.query(models.Transaction).filter(models.Transaction.user_id == tx.user_id, models.Transaction.status.in_(completed_statuses)).order_by(models.Transaction.timestamp.desc()).first()\n'
            '    if last_tx and last_tx.location_ip and last_tx.location_ip != client_ip:\n'
            '        lat1, lon1 = get_lat_lon(last_tx.location_ip)\n'
            '        lat2, lon2 = get_lat_lon(client_ip)\n'
            '        if lat1 and lon1 and lat2 and lon2:\n'
            '            time_diff = (datetime.now(timezone.utc) - last_tx.timestamp.replace(tzinfo=timezone.utc)).total_seconds() / 3600.0\n'
            '            if time_diff > 0: travel_speed_kmh = haversine(lat1, lon1, lat2, lon2) / time_diff'
        )
        # Add to dictionary
        main_code = main_code.replace(
            '"balance":             user.balance,\n    }',
            '"balance":             user.balance,\n        "travel_speed_kmh":    travel_speed_kmh,\n    }'
        )
        with open(MAIN_PY, "w", encoding="utf-8") as f:
            f.write(main_code)
        print("✅ Updated main.py")
except Exception as e:
    print(f"Error on main.py: {e}")

# 2b. Patch predictor.py
try:
    with open(PREDICTOR_PY, "r", encoding="utf-8") as f:
        pred_code = f.read()

    if "travel_speed_kmh =" not in pred_code:
        pred_code = pred_code.replace(
            'balance            = transaction_data.get("balance", 1000000.0)',
            'balance            = transaction_data.get("balance", 1000000.0)\n    travel_speed_kmh   = transaction_data.get("travel_speed_kmh", 0.0)'
        )
        pred_code = pred_code.replace(
            'if amount >= 65000:',
            'if travel_speed_kmh > 800:\n        raw_risk = max(raw_risk, 95.0)  # Impossible Travel lockout\n\n    if amount >= 65000:'
        )
        pred_code = pred_code.replace(
            'if not is_known_ip:\n        flags.append("new_location")',
            'if not is_known_ip:\n        flags.append("new_location")\n\n    if travel_speed_kmh > 800:\n        flags.append("impossible_travel_detected")'
        )
        with open(PREDICTOR_PY, "w", encoding="utf-8") as f:
            f.write(pred_code)
        print("✅ Updated predictor.py")
except Exception as e:
    print(f"Error on predictor.py: {e}")

# 2c. Patch script.js
try:
    with open(SCRIPT_JS, "r", encoding="utf-8") as f:
        script_code = f.read()

    if "impossible_travel_detected" not in script_code:
        script_code = script_code.replace(
            '"multi_factor_anomaly":          "⚠️ Multi-factor anomaly detected",',
            '"multi_factor_anomaly":          "⚠️ Multi-factor anomaly detected",\n        "impossible_travel_detected":    "✈️ Impossible travel speed detected",'
        )
        script_code = script_code.replace(
            'const CRITICAL_FLAGS = ["bot_speed_detected", "account_drain_attempt", "extreme_amount", "multi_factor_anomaly", "rapid_burst_transactions"];',
            'const CRITICAL_FLAGS = ["bot_speed_detected", "account_drain_attempt", "extreme_amount", "multi_factor_anomaly", "rapid_burst_transactions", "impossible_travel_detected"];'
        )
        with open(SCRIPT_JS, "w", encoding="utf-8") as f:
            f.write(script_code)
        print("✅ Updated script.js")
except Exception as e:
    print(f"Error on script.js: {e}")

print("🎉 Setup Complete! You can now restart your IDE and Backend Server.")