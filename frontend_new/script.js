const API_BASE = "http://127.0.0.1:8000/api";
const activeUserId = localStorage.getItem("cf_user_id");
const activeUserName = localStorage.getItem("cf_username");

// --- ROUTER: Run specific logic based on the page ---
if (document.getElementById("loginForm")) initAuthPage();
if (document.getElementById("transactionList")) initDashboardPage();
if (document.getElementById("sendMoneyButton")) initTransferPage();

// ========================================
// 1. AUTHENTICATION PAGE LOGIC
// ========================================
function initAuthPage() {
    const tabLogin = document.getElementById("tabLogin");
    const tabRegister = document.getElementById("tabRegister");
    const loginForm = document.getElementById("loginForm");
    const registerForm = document.getElementById("registerForm");
    const authMessage = document.getElementById("auth-message");

    // UI Toggles
    tabLogin.addEventListener("click", () => {
        loginForm.classList.remove("hidden");
        registerForm.classList.add("hidden");
        tabLogin.style.background = "linear-gradient(135deg, #4c9df5, #2879e8)";
        tabLogin.style.color = "white";
        tabRegister.style.background = "#15191e";
        tabRegister.style.color = "#8993a0";
        document.getElementById("authTitle").innerText = "Welcome back";
        document.getElementById("authSubtitle").innerText = "Sign in to access your secure account";
        authMessage.innerText = "";
    });

    tabRegister.addEventListener("click", () => {
        registerForm.classList.remove("hidden");
        loginForm.classList.add("hidden");
        tabRegister.style.background = "linear-gradient(135deg, #4c9df5, #2879e8)";
        tabRegister.style.color = "white";
        tabLogin.style.background = "#15191e";
        tabLogin.style.color = "#8993a0";
        document.getElementById("authTitle").innerText = "Join CyberForge";
        document.getElementById("authSubtitle").innerText = "Create a new secure account";
        authMessage.innerText = "";
    });

    // Sign Up Logic
    registerForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const user = document.getElementById("regUsername").value;
        const pass = document.getElementById("regPassword").value;
        document.getElementById("regBtn").innerText = "Registering...";

        try {
            const response = await fetch(`${API_BASE}/users/register`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username: user, password: pass })
            });
            authMessage.style.color = "#6fe19a";
            authMessage.innerText = "Account created! Please Sign In.";
            setTimeout(() => tabLogin.click(), 1500);
        } catch (error) {
            authMessage.style.color = "#ffc45c";
            authMessage.innerText = "Connection Error.";
        }
        document.getElementById("regBtn").innerText = "Create Account";
    });

    // Sign In Logic
    loginForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const user = document.getElementById("username").value;
        const pass = document.getElementById("password").value;
        document.getElementById("loginBtn").innerText = "Authenticating...";

        try {
            const response = await fetch(`${API_BASE}/users/login`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username: user, password: pass })
            });
            const data = await response.json();

            if (data.status === "success") {
                localStorage.setItem("cf_user_id", data.user_id);
                localStorage.setItem("cf_username", data.username);
                window.location.href = "dashboard.html";
            } else {
                authMessage.style.color = "#ffc45c";
                authMessage.innerText = "Invalid credentials.";
                document.getElementById("loginBtn").innerText = "Sign in securely";
            }
        } catch (error) {
            authMessage.style.color = "#ffc45c";
            authMessage.innerText = "Server offline.";
            document.getElementById("loginBtn").innerText = "Sign in securely";
        }
    });
}

// ========================================
// 2. DASHBOARD PAGE LOGIC
// ========================================
async function initDashboardPage() {
    if (!activeUserId) {
        window.location.href = "index.html";
        return;
    }

    // Set Name and Avatar
    document.getElementById("welcomeName").innerText = activeUserName;
    document.getElementById("navProfileName").innerText = activeUserName;
    document.getElementById("userAvatar").innerText = activeUserName.charAt(0).toUpperCase();

    // ========================================
    // PROFILE MODAL LOGIC
    // ========================================
    const profileModal = document.getElementById("profileModal");
    const navProfile = document.getElementById("navProfile");
    const userAvatar = document.getElementById("userAvatar");
    const closeProfileModal = document.getElementById("closeProfileModal");

    const toggleProfileModal = () => {
        profileModal.classList.toggle("hidden");
        document.getElementById("modalUserName").innerText = activeUserName;
    };

    if (navProfile) navProfile.addEventListener("click", toggleProfileModal);
    if (userAvatar) userAvatar.addEventListener("click", toggleProfileModal);
    if (closeProfileModal) closeProfileModal.addEventListener("click", toggleProfileModal);

    document.getElementById("modalLogoutBtn").addEventListener("click", () => {
        localStorage.clear();
        window.location.href = "index.html";
    });

    // PIN Management Logic
    const handlePinUpdate = async () => {
        const newPin = prompt("Enter your new 4-digit transaction PIN:");
        if (newPin && newPin.length === 4 && !isNaN(newPin)) {
            try {
                const res = await fetch(`${API_BASE}/users/${activeUserId}/pin`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ pin: newPin })
                });
                const data = await res.json();
                alert(data.message);
            } catch (err) {
                alert("Failed to connect to server.");
            }
        } else if (newPin) {
            alert("Invalid format. PIN must be exactly 4 numbers.");
        }
    };

    document.getElementById("setPinBtn").addEventListener("click", handlePinUpdate);
    document.getElementById("resetPinBtn").addEventListener("click", handlePinUpdate);

    // Tab Navigation: Home vs Activity
    const navHome = document.getElementById("navHome");
    const navActivity = document.getElementById("navActivity");
    const homeWelcome = document.getElementById("homeWelcome");
    const homeActions = document.getElementById("homeActions");

    if (navActivity && navHome) {
        navActivity.addEventListener("click", () => {
            if (homeWelcome) homeWelcome.style.display = "none";
            if (homeActions) homeActions.style.display = "none";
            navHome.classList.remove("active");
            navActivity.classList.add("active");
        });

        navHome.addEventListener("click", () => {
            if (homeWelcome) homeWelcome.style.display = "";
            if (homeActions) homeActions.style.display = "";
            navActivity.classList.remove("active");
            navHome.classList.add("active");
        });
    }

    // Fetch history from FastAPI
    const response = await fetch(`${API_BASE}/transactions/recent/${activeUserId}`);
    const transactions = await response.json();
    const list = document.getElementById("transactionList");

    if (transactions.length === 0) {
        list.innerHTML = `<p style="color:#858e9a; padding:15px 0; text-align:center;">No recent transactions.</p>`;
        return;
    }

    // Render transactions
    transactions.forEach(tx => {
        const item = document.createElement("div");
        item.className = "transaction";
        item.style = "border-bottom: 1px solid #252b32; padding: 15px 3px;";
        
        const initial = tx.recipient_account.charAt(0).toUpperCase();
        const dateStr = new Date(tx.timestamp).toLocaleDateString("en-IN");
        
        item.innerHTML = `
            <div class="transaction-icon" style="background: #202630; color: #79b6ff;">${initial}</div>
            <div class="transaction-info">
                <h3 style="color: #f0f2f5; font-size:15px;">${tx.recipient_account}</h3>
                <p style="color: #858e9a; font-size:12px; margin-top:4px;">${dateStr} • ${tx.status}</p>
            </div>
            <strong style="color: #ff7474; margin-left:auto;">- Rs.${tx.amount.toLocaleString("en-IN")}</strong>
        `;
        list.appendChild(item);
    });
}

// ========================================
// 3. TRANSFER PAGE LOGIC (with Typing Speed Biometrics)
// ========================================
function initTransferPage() {
    if (!activeUserId) window.location.href = "index.html";

    // -----------------------------------------------
    // TYPING SPEED TRACKER
    // -----------------------------------------------
    let firstKeystrokeTime = null;

    const recipientInput = document.getElementById("recipient");
    const amountInput = document.getElementById("amount");

    const trackKeystroke = () => {
        if (firstKeystrokeTime === null) {
            firstKeystrokeTime = Date.now();
        }
    };

    recipientInput.addEventListener("keydown", trackKeystroke);
    amountInput.addEventListener("keydown", trackKeystroke);

    // -----------------------------------------------
    // FLAG LABEL HELPER
    // -----------------------------------------------
    const FLAG_LABELS = {
        "new_location":           "New location detected",
        "new_device":             "New device detected",
        "bot_speed_detected":     "Bot-like speed detected",
        "unusual_typing_pattern": "Unusual typing pattern",
        "unusual_amount":         "Unusual transaction amount",
        "unusual_hour":           "Transaction at unusual hour",
    };

    function renderFlags(flags) {
        const container = document.getElementById("riskFlags");
        if (!container) return;
        container.innerHTML = "";
        flags.forEach(flag => {
            const label = FLAG_LABELS[flag] || flag;
            const span = document.createElement("span");
            span.innerText = label;
            span.style.cssText = "background:#2a1a1a; color:#ff9a6c; font-size:11px; padding:4px 10px; border-radius:12px; border:1px solid #3d2020;";
            container.appendChild(span);
        });
    }

    // -----------------------------------------------
    // SEND MONEY HANDLER
    // -----------------------------------------------
    document.getElementById("sendMoneyButton").addEventListener("click", async () => {
        const recipient = document.getElementById("recipient").value;
        const amount = document.getElementById("amount").value;

        if (!recipient || !amount) return alert("Please fill all details.");

        // Calculate typing speed (ms from first keystroke to submit click)
        const typingSpeedMs = firstKeystrokeTime ? (Date.now() - firstKeystrokeTime) : null;

        // 1. Show Security Animation Screen
        document.getElementById("sendMoneyButton").disabled = true;
        document.querySelector(".cf-transfer-card").classList.add("hidden");
        document.getElementById("transferSecurity").classList.remove("hidden");

        // 2. Build payload with real device info + typing speed (IP auto-detected server-side)
        const payload = {
            user_id: parseInt(activeUserId),
            amount: parseFloat(amount),
            recipient: recipient,
            device_info: navigator.userAgent,
            typing_speed_ms: typingSpeedMs,
        };

        try {
            const response = await fetch(`${API_BASE}/transactions/transfer`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const data = await response.json();

            // 3. Animate the 4-step security verification flow
            // Step 1: Device verification (after 600ms)
            setTimeout(() => {
                document.getElementById("transferDeviceCheck").className = "transfer-check-icon verified";
                document.getElementById("transferDeviceCheck").innerText = "\u2713";

                // Step 2: Behavioral biometrics (after 1200ms)
                setTimeout(() => {
                    document.getElementById("transferBehaviorCheck").className = "transfer-check-icon verified";
                    document.getElementById("transferBehaviorCheck").innerText = "\u2713";
                    if (typingSpeedMs) {
                        document.getElementById("transferBehaviorStatus").innerText = `Typing speed: ${(typingSpeedMs / 1000).toFixed(1)}s`;
                    }

                    // Step 3: Risk assessment (after 1800ms)
                    setTimeout(() => {
                        document.getElementById("transferRiskCheck").className = "transfer-check-icon verified";
                        document.getElementById("transferRiskCheck").innerText = "\u2713";
                        document.getElementById("riskScore").innerText = `Risk Score: ${data.risk_score} / 100`;

                        // Color the risk score
                        if (data.risk_score >= 80) {
                            document.getElementById("riskScore").classList.add("high-risk");
                        } else if (data.risk_score >= 25) {
                            document.getElementById("riskScore").style.color = "#ffc45c";
                        } else {
                            document.getElementById("riskScore").style.color = "#6fe19a";
                        }

                        // Render flags
                        renderFlags(data.flags || []);

                        // Step 4: Authentication decision (after 2400ms)
                        setTimeout(() => {
                            handleAuthDecision(data, payload, amount, recipient);
                        }, 600);

                    }, 600);
                }, 600);
            }, 600);

        } catch (error) {
            alert("Backend disconnected.");
            document.getElementById("sendMoneyButton").disabled = false;
        }
    });

    // -----------------------------------------------
    // HANDLE AUTH DECISION BASED ON AI RESPONSE
    // -----------------------------------------------
    function handleAuthDecision(data, payload, amount, recipient) {
        if (data.action === "REQUIRE_HARDWARE_AUTH") {
            document.getElementById("transferHardwareCheck").className = "transfer-check-icon warning";
            document.getElementById("transferHardwareCheck").innerText = "!";
            document.getElementById("transferHardwareStatus").innerText = "ESP32 hardware required!";
            document.getElementById("transferStatusTitle").innerText = "High-risk transaction";
            document.getElementById("riskScore").classList.add("high-risk");
        }
        else if (data.action === "REQUIRE_OTP") {
            document.getElementById("transferHardwareCheck").className = "transfer-check-icon warning";
            document.getElementById("transferHardwareCheck").innerText = "!";
            document.getElementById("transferHardwareStatus").innerText = "OTP sent to phone.";
            document.getElementById("transferStatusTitle").innerText = "Verification Required";
        }
        else if (data.action === "REQUIRE_SETUP") {
            alert("Security Alert: " + data.message);
            window.location.href = "dashboard.html";
        }
        else if (data.action === "REQUIRE_PIN") {
            const enteredPin = prompt("Security Check: Enter your 4-digit Transaction PIN to approve this transfer.");

            if (!enteredPin) {
                alert("Transaction cancelled.");
                window.location.reload();
                return;
            }

            // Resend with PIN attached
            payload.pin = enteredPin;
            fetch(`${API_BASE}/transactions/transfer`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            }).then(res => res.json()).then(pinData => {
                if (pinData.action === "INVALID_PIN") {
                    alert("Transaction Failed: " + pinData.message);
                    window.location.reload();
                } else {
                    // PIN correct — show success!
                    document.getElementById("transferHardwareCheck").className = "transfer-check-icon verified";
                    document.getElementById("transferHardwareCheck").innerText = "\u2713";
                    document.getElementById("transferHardwareStatus").innerText = "PIN Verified";
                    document.getElementById("transferStatusTitle").innerText = "Transaction approved";

                    setTimeout(() => {
                        document.getElementById("transferSecurity").classList.add("hidden");
                        document.getElementById("transactionResult").classList.remove("hidden");
                        document.getElementById("resultMessage").innerText = `Rs.${amount} sent to ${recipient}.`;
                    }, 1200);
                }
            });
        }
        else {
            // Standard success (ALLOW)
            document.getElementById("transferHardwareCheck").className = "transfer-check-icon verified";
            document.getElementById("transferHardwareCheck").innerText = "\u2713";
            document.getElementById("transferHardwareStatus").innerText = "Authentication not required";
            document.getElementById("transferStatusTitle").innerText = "Transaction approved";

            setTimeout(() => {
                document.getElementById("transferSecurity").classList.add("hidden");
                document.getElementById("transactionResult").classList.remove("hidden");
                document.getElementById("resultMessage").innerText = `Rs.${amount} sent to ${recipient}.`;
            }, 1200);
        }
    }
}