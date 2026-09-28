# CyberForge ESP32 Hardware Security Token — Complete Setup Guide

> **Zero-Button Setup**: You only need an ESP32 + OLED display + 4 wires. The onboard **BOOT** button on the ESP32 is used to approve transactions. No external buttons required!

---

## What You Need

| Item | Quantity |
| :--- | :--- |
| ESP32 Dev Board (ESP-WROOM-32 / NodeMCU-32S) | 1 |
| 0.96" I2C OLED Display (SSD1306, 128×64) | 1 |
| Male-to-Female Jumper Wires | 4 |
| USB Micro / Type-C Cable (for ESP32 to laptop) | 1 |

---

## STEP 1 — Wire the OLED Display to ESP32

Connect these **4 wires** between the OLED display and the ESP32:

```
OLED Display          ESP32 Board
───────────           ──────────
   VCC  ─────────►   3.3V (3V3 pin)
   GND  ─────────►   GND
   SDA  ─────────►   GPIO 19
   SCL  ─────────►   GPIO 22
```

### Pin Connection Table

| OLED Pin | ESP32 Pin | Wire Color (suggestion) |
| :--- | :--- | :--- |
| **VCC** | **3.3V** (3V3) | 🔴 Red |
| **GND** | **GND** | ⚫ Black |
| **SDA** | **GPIO 19** (D19) | 🔵 Blue |
| **SCL** | **GPIO 22** (D22) | 🟡 Yellow |

> **Tip**: Look at the silkscreen labels printed on your ESP32 board to find pins labeled `3V3`, `GND`, `D19`/`19`, and `D22`/`22`.

That's it for wiring! No breadboard needed — just plug the 4 wires directly.

---

## STEP 2 — Install Arduino IDE & ESP32 Support

### 2a. Download Arduino IDE
1. Go to [https://www.arduino.cc/en/software](https://www.arduino.cc/en/software)
2. Download **Arduino IDE 2.x** for Windows
3. Install it (just click Next through the installer)

### 2b. Add ESP32 Board Support
1. Open Arduino IDE
2. Go to **File → Preferences**
3. In the **"Additional Board Manager URLs"** field, paste:
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
4. Click **OK**
5. Go to **Tools → Board → Boards Manager**
6. Search for **esp32**
7. Find **"esp32 by Espressif Systems"** and click **Install** (this takes a few minutes)

### 2c. Install Required Libraries
1. Go to **Tools → Manage Libraries...**
2. Search and install these one by one:
   - **ArduinoJson** (by Benoit Blanchon) — for JSON parsing
   - **Adafruit SSD1306** (by Adafruit) — for the OLED display
   - **Adafruit GFX Library** (by Adafruit) — graphics dependency (install if prompted)

---

## STEP 3 — Configure the Firmware Code

Open the file `hardware/cyberforge_token.ino` in Arduino IDE and update **lines 34–42**:

```cpp
// ==========================================
// 1. CONFIGURATION — UPDATE THESE VALUES
// ==========================================
const char* WIFI_SSID     = "YourWiFiName";         // ← Your 2.4 GHz WiFi name
const char* WIFI_PASSWORD = "YourWiFiPassword";      // ← Your WiFi password

const char* SERVER_BASE_URL = "http://192.168.1.XX:8000"; // ← Your laptop's IP

const int ASSIGNED_USER_ID = 101;                    // ← Your CyberForge user ID
```

### How to find your laptop's IP address:
Open **PowerShell** and run:
```powershell
ipconfig
```
Look for **IPv4 Address** under your Wi-Fi adapter (e.g., `192.168.1.15`).

> **Important**: Your ESP32 and laptop MUST be on the **same Wi-Fi network** (2.4 GHz).

---

## STEP 4 — Flash the Code to ESP32

### If your ESP32 already has other code on it — that's fine! Uploading new code completely overwrites the old code.

1. **Plug the ESP32** into your laptop via USB
2. In Arduino IDE, go to **Tools** and set:
   - **Board**: `ESP32 Dev Module` (or `NodeMCU-32S` depending on your board)
   - **Port**: Select the COM port that appeared (e.g., `COM3`, `COM5`)
   - **Upload Speed**: `115200`
3. Click the **Upload** button (→ arrow icon) in the top-left
4. **When you see "Connecting..."** in the console, **hold down the BOOT button** on the ESP32 for 2-3 seconds, then release
   - Some boards auto-upload without needing the button hold
5. Wait for **"Done uploading"** message

> **Driver Issue?** If no COM port appears:
> - **CP2102 chip**: Install driver from [Silicon Labs](https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers)
> - **CH340 chip**: Install driver from [CH340 Driver](http://www.wch-ic.com/downloads/CH341SER_EXE.html)
> - Check which chip is on your ESP32 board (look at the small IC near the USB port)

---

## STEP 5 — Start the CyberForge Backend

Open **PowerShell** and run:

```powershell
cd e:\cyberforge\backend
.\venv\Scripts\Activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

> **`--host 0.0.0.0`** is critical! Without it, the ESP32 can't reach your backend over WiFi.

---

## STEP 6 — Test It!

1. **Open Arduino Serial Monitor**: In Arduino IDE → **Tools → Serial Monitor** → set baud to **115200**
2. You should see:
   ```
   ========================================
     CyberForge Hardware Security Token
   ========================================
   [OK] OLED display detected (0x3C)
   Connecting to Wi-Fi: YourWiFiName.....
   [OK] WiFi Connected!
   ESP32 IP: 192.168.1.42
   ```
3. The OLED will show **"Token Ready"** with the IP address

### Trigger a High-Risk Transaction:
1. Open `frontend/index.html` in your browser and **log in**
2. Go to **Send Money**
3. Enter:
   - **Recipient**: `Hacker_Account`
   - **Amount**: `₹75,000` or more (triggers risk score ≥ 80)
4. The web app will show: **"⏳ Waiting for ESP32 hardware button press..."**
5. The ESP32 OLED will show:
   ```
   ┌────────────────────┐
   │ AUTH REQUIRED       │
   │────────────────────│
   │ Rs. 75000           │
   │ To: Hacker_Account  │
   │ BOOT:Yes | Wait:No  │
   └────────────────────┘
   ```
6. **Press the BOOT button** on the ESP32 → Transaction approved! ✅
7. **Or wait 30 seconds** → Transaction auto-rejected ❌

---

## How It Works (Architecture)

```
┌──────────────┐    HTTP POST     ┌──────────────────┐
│  Web Browser  │ ──────────────► │  FastAPI Backend  │
│  (Frontend)   │                 │  (main.py)        │
└──────────────┘                  └────────┬─────────┘
       ▲                                   │
       │ polls /status                     │ sets status = "ESP32_Awaiting"
       │                                   │
       │                          ┌────────▼─────────┐
       │    HTTP POST /verify     │     ESP32 Token   │
       └──────────────────────────│   (polls every    │
                                  │    2 seconds)     │
                                  │                   │
                                  │  BOOT btn pressed │
                                  │  → sends APPROVED │
                                  └───────────────────┘
```

1. **Risk ≥ 80** → Backend sets transaction to `ESP32_Awaiting`
2. **ESP32 polls** `/api/hardware/pending_requests` every 2 seconds
3. **OLED shows** the amount & recipient, LED blinks rapidly
4. **User presses BOOT** → ESP32 sends `APPROVED` to `/api/hardware/verify`
5. **Backend completes** the transaction, deducts balance
6. **Browser auto-updates** (polls `/api/transactions/status/`) and shows success animation

---

## Troubleshooting

| Problem | Solution |
| :--- | :--- |
| **OLED blank/not detected** | Check SDA→GPIO19, SCL→GPIO22 wiring. Try swapping SDA/SCL. |
| **WiFi won't connect** | Ensure 2.4 GHz network (ESP32 doesn't support 5 GHz). Check SSID/password. |
| **ESP32 can't reach backend** | Run backend with `--host 0.0.0.0`. Check IP with `ipconfig`. |
| **No COM port in Arduino** | Install CP2102 or CH340 USB driver (see Step 4). |
| **Upload fails at "Connecting..."** | Hold BOOT button while uploading, release after "Connecting..." appears. |
| **OLED shows address 0x3D** | Change `0x3C` to `0x3D` on line 116 of the `.ino` file. |
| **Transaction not appearing on ESP32** | Ensure `ASSIGNED_USER_ID` in code matches your logged-in user ID. |
