const API_BASE = "http://127.0.0.1:8000/api";
let activeUserId = null;

// UI Toggles
const tabLogin = document.getElementById("tab-login");
const tabRegister = document.getElementById("tab-register");
const loginForm = document.getElementById("loginForm");
const registerForm = document.getElementById("registerForm");
const authMessage = document.getElementById("auth-message");

tabLogin.addEventListener("click", () => {
    tabLogin.classList.add("active-tab");
    tabRegister.classList.remove("active-tab");
    loginForm.style.display = "block";
    registerForm.style.display = "none";
    authMessage.innerText = "";
});

tabRegister.addEventListener("click", () => {
    tabRegister.classList.add("active-tab");
    tabLogin.classList.remove("active-tab");
    registerForm.style.display = "block";
    loginForm.style.display = "none";
    authMessage.innerText = "";
});

// 1. REGISTER LOGIC
registerForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const user = document.getElementById("reg-user").value;
    const pass = document.getElementById("reg-pass").value;

    authMessage.innerText = "Encrypting credentials...";
    authMessage.style.color = "#60a5fa";

    try {
        const response = await fetch(`${API_BASE}/users/register`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username: user, password: pass })
        });
        const data = await response.json();

        authMessage.innerText = "Registration complete! You may now sign in.";
        authMessage.style.color = "#10b981";
        setTimeout(() => tabLogin.click(), 2000); // Auto-switch to login after 2 seconds
    } catch (error) {
        authMessage.innerText = "Error: Cannot reach server.";
        authMessage.style.color = "#ef4444";
    }
});

// 2. LOGIN LOGIC
loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const user = document.getElementById("login-user").value;
    const pass = document.getElementById("login-pass").value;

    authMessage.innerText = "Authenticating hardware...";
    authMessage.style.color = "#60a5fa";

    try {
        const response = await fetch(`${API_BASE}/users/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username: user, password: pass })
        });
        const data = await response.json();

        if (data.status === "success") {
            activeUserId = data.user_id;
            document.getElementById("auth-view").style.display = "none";
            document.getElementById("dashboard-view").style.display = "block";
            document.getElementById("display-name").innerText = data.username;
            fetchHistory();
        } else {
            authMessage.innerText = "Access Denied: Invalid credentials.";
            authMessage.style.color = "#ef4444";
        }
    } catch (error) {
        authMessage.innerText = "Connection Error.";
        authMessage.style.color = "#ef4444";
    }
});

// 3. TRANSFER LOGIC
document.getElementById("transferForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const msgBox = document.getElementById("transfer-message");
    msgBox.innerText = "Processing via secure relay...";
    msgBox.style.color = "#60a5fa";

    const payload = {
        user_id: activeUserId,
        amount: parseFloat(document.getElementById("amount").value),
        recipient: document.getElementById("recipient").value,
        device_info: "Web_Browser",
        location_ip: "127.0.0.1"
    };

    const response = await fetch(`${API_BASE}/transactions/transfer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    });

    const data = await response.json();

    if (data.action === "REQUIRE_HARDWARE_AUTH") {
        msgBox.innerHTML = `⚠️ <b>Hardware Auth Required</b> (Score: ${data.risk_score})`;
        msgBox.style.color = "#f59e0b";
    } else if (data.action === "REQUIRE_OTP") {
        msgBox.innerHTML = `📱 <b>OTP Sent</b> (Score: ${data.risk_score})`;
        msgBox.style.color = "#3b82f6";
    } else {
        msgBox.innerHTML = `✅ <b>Transfer Approved</b> (Score: ${data.risk_score})`;
        msgBox.style.color = "#10b981";
    }

    fetchHistory();
});

// 4. FETCH HISTORY
async function fetchHistory() {
    if (!activeUserId) return;
    const response = await fetch(`${API_BASE}/transactions/recent/${activeUserId}`);
    const transactions = await response.json();

    const list = document.getElementById("history-list");
    list.innerHTML = "";

    transactions.forEach(tx => {
        const li = document.createElement("li");
        li.innerHTML = `<span>To: ${tx.recipient_account}</span> <span>₹${tx.amount} <small>(${tx.status})</small></span>`;
        list.appendChild(li);
    });
}

// 5. LOGOUT
document.getElementById("logoutBtn").addEventListener("click", () => {
    activeUserId = null;
    document.getElementById("loginForm").reset();
    document.getElementById("registerForm").reset();
    document.getElementById("transferForm").reset();
    document.getElementById("auth-message").innerText = "";
    document.getElementById("dashboard-view").style.display = "none";
    document.getElementById("auth-view").style.display = "block";
});