/*
 * =====================================================================================
 * CyberForge ESP32 Hardware Security Token
 * =====================================================================================
 * 
 * Hardware:
 *   - ESP32 Development Board (ESP-WROOM-32 / NodeMCU ESP32)
 *   - Built-in BOOT button on ESP32 (GPIO 0): Press to APPROVE (No external buttons needed!)
 *   - Or Jumper Wire in GPIO 18: Touch to GND to APPROVE
 *   - Or Jumper Wire in GPIO 21: Touch to GND to REJECT (or wait 30s timeout)
 *   - 0.96" I2C OLED Display (SSD1306 128x64):
 *       - VCC -> 3.3V
 *       - GND -> GND
 *       - SDA -> GPIO 19
 *       - SCL -> GPIO 22
 *   - Onboard LED on GPIO 2 (Status indicator)
 * 
 * Required Arduino Libraries:
 *   - ArduinoJson (by Benoit Blanchon, v6 or v7)
 *   - Adafruit SSD1306 & Adafruit GFX (by Adafruit) [Optional if using OLED]
 * =====================================================================================
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// ==========================================
// 1. CONFIGURATION — UPDATE THESE VALUES
// ==========================================
const char* WIFI_SSID     = "ARUSH-PC 0127";        // 2.4 GHz WiFi SSID
const char* WIFI_PASSWORD = "86C2/89m";    // WiFi Password

// Backend URL: Replace with your laptop's Wi-Fi IP address
// Active Wi-Fi IP detected: http://10.130.152.251:8000
// Line 39 (Laptop Hotspot IP):
const char* SERVER_BASE_URL = "https://cyberforge-22d1.onrender.com";


// The CyberForge User ID this physical token belongs to (e.g. 101 for Arush)
const int ASSIGNED_USER_ID = 101;

// Unique hardware token identifier reported in audit logs
const char* HARDWARE_TOKEN_ID = "ESP32_CF_TOKEN_01";

// ==========================================
// 2. PIN DEFINITIONS
// ==========================================
#define ONBOARD_BOOT_BUTTON 0   // Built-in physical button on ESP32 board!
#define BUTTON_APPROVE_PIN 18   // Optional wire: touch to GND to approve
#define BUTTON_REJECT_PIN  21   // Optional wire: touch to GND to reject
#define STATUS_LED_PIN     2    // Onboard blue LED

// OLED Configuration (128x64 I2C)
#define OLED_SDA_PIN       19   // I2C Data line (GPIO 19)
#define OLED_SCL_PIN       22   // I2C Clock line (GPIO 22)
#define SCREEN_WIDTH       128
#define SCREEN_HEIGHT      64
#define OLED_RESET         -1
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);
bool oledAvailable = false;

// ==========================================
// DISPLAY HELPER FUNCTIONS
// ==========================================
void showScreen(const char* title, const char* line1, const char* line2 = "", const char* line3 = "") {
  Serial.println("----------------------------------------");
  Serial.printf("[%s]\n", title);
  if (strlen(line1) > 0) Serial.println(line1);
  if (strlen(line2) > 0) Serial.println(line2);
  if (strlen(line3) > 0) Serial.println(line3);
  Serial.println("----------------------------------------");

  if (!oledAvailable) return;

  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);

  // Title bar
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.println(title);
  display.drawLine(0, 9, 128, 9, SSD1306_WHITE);

  // Lines
  display.setCursor(0, 14);
  display.println(line1);
  display.setCursor(0, 28);
  display.println(line2);
  display.setCursor(0, 44);
  display.println(line3);

  display.display();
}

// ==========================================
// SETUP
// ==========================================
void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n\n========================================");
  Serial.println("  CyberForge Hardware Security Token");
  Serial.println("========================================");

  // Pin modes (Internal Pullups: pressing connects to GND)
  pinMode(ONBOARD_BOOT_BUTTON, INPUT_PULLUP);
  pinMode(BUTTON_APPROVE_PIN, INPUT_PULLUP);
  pinMode(BUTTON_REJECT_PIN, INPUT_PULLUP);
  pinMode(STATUS_LED_PIN, OUTPUT);
  digitalWrite(STATUS_LED_PIN, LOW);

  // Initialize OLED (Address 0x3C is standard)
  Wire.begin(OLED_SDA_PIN, OLED_SCL_PIN);
  if (display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    oledAvailable = true;
    display.clearDisplay();
    display.display();
    Serial.println("[OK] OLED display detected (0x3C)");
  } else {
    Serial.println("[INFO] OLED not detected. Running in Serial / LED mode.");
  }

  // Connect to Wi-Fi
  showScreen("CyberForge Token", "Connecting to WiFi...", WIFI_SSID);
  Serial.printf("Connecting to Wi-Fi: %s", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    digitalWrite(STATUS_LED_PIN, !digitalRead(STATUS_LED_PIN));
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    digitalWrite(STATUS_LED_PIN, HIGH);
    Serial.println("\n[OK] WiFi Connected!");
    Serial.print("ESP32 IP: ");
    Serial.println(WiFi.localIP());

    char ipMsg[32];
    snprintf(ipMsg, sizeof(ipMsg), "IP: %s", WiFi.localIP().toString().c_str());
    showScreen("Token Ready", "Connected to WiFi", ipMsg, "Monitoring transactions...");
    delay(2000);
  } else {
    digitalWrite(STATUS_LED_PIN, LOW);
    Serial.println("\n[ERROR] WiFi connection failed. Check credentials.");
    showScreen("WiFi Error", "Could not connect", "Check SSID & Pass");
  }
}

// ==========================================
// SEND VERIFICATION RESULT TO BACKEND
// ==========================================
bool sendVerification(int transactionId, const char* status) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[ERROR] WiFi not connected. Cannot send verification.");
    return false;
  }

  HTTPClient http;
  String url = String(SERVER_BASE_URL) + "/api/hardware/verify";
  http.begin(url);
  http.addHeader("Content-Type", "application/json");

  // Construct JSON payload
  StaticJsonDocument<200> doc;
  doc["transaction_id"] = transactionId;
  doc["hardware_id"]    = HARDWARE_TOKEN_ID;
  doc["status"]         = status;

  String requestBody;
  serializeJson(doc, requestBody);

  Serial.printf("[HTTP POST] Sending to %s -> %s\n", url.c_str(), requestBody.c_str());
  int httpCode = http.POST(requestBody);

  bool success = false;
  if (httpCode > 0) {
    String response = http.getString();
    Serial.printf("[HTTP %d] Response: %s\n", httpCode, response.c_str());
    success = (httpCode == 200);
  } else {
    Serial.printf("[HTTP ERROR] Failed, code: %d\n", httpCode);
  }

  http.end();
  return success;
}

// ==========================================
// HANDLE PENDING TRANSACTION (PROMPT USER)
// ==========================================
void handlePendingTransaction(int transactionId, float amount, const char* recipient) {
  Serial.printf("\n🚨 HIGH RISK TRANSACTION DETECTED!\n");
  Serial.printf("   Transaction ID : %d\n", transactionId);
  Serial.printf("   Amount         : Rs. %.2f\n", amount);
  Serial.printf("   Recipient      : %s\n", recipient);
  Serial.println("   -> Press onboard BOOT button (or touch GPIO 18 to GND) to APPROVE");
  Serial.println("   -> Touch GPIO 21 to GND (or wait 30s) to REJECT\n");

  char amtStr[32];
  snprintf(amtStr, sizeof(amtStr), "Rs. %.0f", amount);
  char toStr[32];
  snprintf(toStr, sizeof(toStr), "To: %s", recipient);

  showScreen("AUTH REQUIRED", amtStr, toStr, "BOOT:Yes | Wait:No");

  // 30-Second timeout countdown loop
  unsigned long startTime = millis();
  const unsigned long TIMEOUT_MS = 30000;
  bool decided = false;
  const char* finalDecision = "REJECTED";

  while ((millis() - startTime) < TIMEOUT_MS && !decided) {
    // Fast blink status LED during prompt
    digitalWrite(STATUS_LED_PIN, (millis() / 200) % 2);

    // Read buttons or wire-touches (Active LOW due to INPUT_PULLUP)
    bool isApprovePressed = (digitalRead(ONBOARD_BOOT_BUTTON) == LOW) || (digitalRead(BUTTON_APPROVE_PIN) == LOW);
    bool isRejectPressed  = (digitalRead(BUTTON_REJECT_PIN) == LOW);

    if (isApprovePressed) {
      delay(50); // Debounce
      if ((digitalRead(ONBOARD_BOOT_BUTTON) == LOW) || (digitalRead(BUTTON_APPROVE_PIN) == LOW)) {
        finalDecision = "APPROVED";
        decided = true;
        Serial.println(">>> User Confirmed: APPROVE (BOOT button or GPIO 18 wire touched to GND)");
      }
    } else if (isRejectPressed) {
      delay(50); // Debounce
      if (digitalRead(BUTTON_REJECT_PIN) == LOW) {
        finalDecision = "REJECTED";
        decided = true;
        Serial.println(">>> User Confirmed: REJECT (GPIO 21 wire touched to GND)");
      }
    }

    delay(20);
  }

  digitalWrite(STATUS_LED_PIN, HIGH);

  if (!decided) {
    Serial.println(">>> Authorization TIMED OUT! Defaulting to REJECTED.");
    finalDecision = "REJECTED";
  }

  // Display outcome
  if (strcmp(finalDecision, "APPROVED") == 0) {
    showScreen("TRANSACTION APPROVED", "Physical Token Verified", "Sending approval...");
  } else {
    showScreen("TRANSACTION BLOCKED", "Unauthorized / Rejected", "Sending rejection...");
  }

  // Transmit decision to backend
  sendVerification(transactionId, finalDecision);

  delay(3000);
  showScreen("CyberForge Token", "System Active", "Monitoring for alerts");
}

// ==========================================
// MAIN POLLING LOOP
// ==========================================
void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    digitalWrite(STATUS_LED_PIN, LOW);
    Serial.println("[WARN] WiFi lost. Reconnecting...");
    WiFi.reconnect();
    delay(5000);
    return;
  }

  digitalWrite(STATUS_LED_PIN, HIGH);

  // Poll backend for any high-risk transaction awaiting hardware auth
  HTTPClient http;
  String url = String(SERVER_BASE_URL) + "/api/hardware/pending_requests?user_id=" + String(ASSIGNED_USER_ID);
  http.begin(url);
  http.setTimeout(2000);

  int httpCode = http.GET();

  if (httpCode == 200) {
    String payload = http.getString();
    
    // Parse JSON response
    StaticJsonDocument<300> doc;
    DeserializationError error = deserializeJson(doc, payload);

    if (!error) {
      const char* status = doc["status"];
      if (status && strcmp(status, "PENDING_REQUEST") == 0) {
        int txId = doc["transaction_id"];
        float amount = doc["amount"];
        const char* recipient = doc["recipient"];
        handlePendingTransaction(txId, amount, recipient ? recipient : "Unknown");
      }
    }
  } else if (httpCode > 0) {
    // Non-200 HTTP code
  } else {
    // Connection error (backend offline or incorrect IP)
    Serial.printf("[WARN] Could not reach backend: %s\n", SERVER_BASE_URL);
  }

  http.end();

  // Poll every 2 seconds
  delay(2000);
}
