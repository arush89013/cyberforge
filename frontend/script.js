// ========================================
// CYBERFORGE FRONTEND
// Complete Demo Frontend
// ========================================


// ========================================
// DEMO RISK SETTINGS
// ========================================

// LOW    = Direct approval
// MEDIUM = OTP verification
// HIGH   = ESP32 authentication

const DEMO_RISK_MODE = "HIGH";


function getDemoRiskScore() {

    if (DEMO_RISK_MODE === "LOW") {
        return 20;
    }

    if (DEMO_RISK_MODE === "MEDIUM") {
        return 55;
    }

    return 90;
}


// ========================================
// COMMON HELPERS
// ========================================

function getTransactions() {

    return JSON.parse(
        localStorage.getItem("cyberforge_transactions")
    ) || [];
}


function saveTransaction(recipient, amount, status = "Completed") {

    const transaction = {
        recipient: recipient,
        amount: Number(amount),
        date: new Date().toLocaleString("en-IN"),
        status: status
    };

    let transactions = getTransactions();

    transactions.unshift(transaction);

    transactions = transactions.slice(0, 10);

    localStorage.setItem(
        "cyberforge_transactions",
        JSON.stringify(transactions)
    );

    return transaction;
}


function showMessage(title, message, buttonText = "Done") {

    let modal = document.getElementById("cyberforgeModal");

    if (!modal) {

        modal = document.createElement("div");

        modal.id = "cyberforgeModal";

        modal.innerHTML = `
            <div class="cf-modal-box">

                <button class="cf-modal-close">×</button>

                <div class="cf-modal-icon">🔐</div>

                <h2 id="cfModalTitle"></h2>

                <p id="cfModalMessage"></p>

                <button id="cfModalButton" class="cf-modal-button">
                    Done
                </button>

            </div>
        `;

        document.body.appendChild(modal);

        addModalStyles();

        modal.querySelector(".cf-modal-close")
            .addEventListener("click", closeModal);

        modal.querySelector("#cfModalButton")
            .addEventListener("click", closeModal);
    }

    document.getElementById("cfModalTitle").innerText = title;

    document.getElementById("cfModalMessage").innerText = message;

    document.getElementById("cfModalButton").innerText = buttonText;

    modal.classList.add("show");
}


function closeModal() {

    const modal =
        document.getElementById("cyberforgeModal");

    if (modal) {
        modal.classList.remove("show");
    }
}


function addModalStyles() {

    if (document.getElementById("cfModalStyles")) {
        return;
    }

    const style = document.createElement("style");

    style.id = "cfModalStyles";

    style.innerHTML = `

        #cyberforgeModal {
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,.72);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 9999;
            padding: 20px;
        }

        #cyberforgeModal.show {
            display: flex;
        }

        .cf-modal-box {
            width: min(420px, 100%);
            background: #151a20;
            border: 1px solid #2a323c;
            border-radius: 24px;
            padding: 30px;
            text-align: center;
            position: relative;
            box-shadow: 0 25px 70px rgba(0,0,0,.55);
        }

        .cf-modal-close {
            position: absolute;
            top: 12px;
            right: 16px;
            background: transparent;
            border: 0;
            color: #858e9a;
            font-size: 28px;
            cursor: pointer;
        }

        .cf-modal-icon {
            width: 65px;
            height: 65px;
            margin: 5px auto 18px;
            border-radius: 50%;
            background: #1e2d42;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 28px;
        }

        .cf-modal-box h2 {
            color: #fff;
            margin-bottom: 10px;
        }

        .cf-modal-box p {
            color: #9da6b2;
            line-height: 1.6;
            margin-bottom: 22px;
        }

        .cf-modal-button {
            width: 100%;
            padding: 13px;
            border: 0;
            border-radius: 12px;
            background: #2879e8;
            color: white;
            font-weight: 600;
            cursor: pointer;
        }

        .cf-modal-input {
            width: 100%;
            padding: 13px;
            margin: 8px 0;
            box-sizing: border-box;
            background: #0d0f11;
            border: 1px solid #303944;
            border-radius: 10px;
            color: white;
        }

        .cf-modal-action {
            width: 100%;
            padding: 13px;
            margin-top: 10px;
            border: 0;
            border-radius: 12px;
            background: #2879e8;
            color: white;
            font-weight: 600;
            cursor: pointer;
        }
    `;

    document.head.appendChild(style);
}


// ========================================
// SIMPLE FEATURE MODAL
// ========================================

function showFeature(title, message) {

    showMessage(
        title,
        message,
        "Continue"
    );
}


// ========================================
// 1. LIVE LOGIN SECURITY (FASTAPI)
// ========================================

const loginForm = document.getElementById("loginForm");

if (loginForm) {
    loginForm.addEventListener("submit", async function (event) {
        event.preventDefault();

        const username = document.getElementById("username").value.trim();
        const password = document.getElementById("password").value;
        const securityStatus = document.getElementById("securityStatus");
        const statusTitle = document.getElementById("statusTitle");
        const statusMessage = document.getElementById("statusMessage");
        const loginButton = document.querySelector(".cf-login-button");
        const deviceCheck = document.getElementById("deviceCheck");
        const locationCheck = document.getElementById("locationCheck");
        const hardwareCheck = document.getElementById("hardwareCheck");
        const hardwareStatus = document.getElementById("hardwareStatus");
        const loginRiskScore = document.getElementById("loginRiskScore");

        if (username === "" || password === "") {
            alert("Please enter username and password.");
            return;
        }

        // 1. Set UI to Loading State
        securityStatus.classList.remove("hidden");
        loginButton.disabled = true;
        loginButton.innerText = "Security check running...";
        statusTitle.innerText = "Analyzing login risk...";
        statusMessage.innerText = "CyberForge is checking your request";
        
        deviceCheck.className = "check-icon checking";
        deviceCheck.innerText = "◉";
        locationCheck.className = "check-icon checking";
        locationCheck.innerText = "◉";
        hardwareCheck.className = "check-icon pending";
        hardwareCheck.innerText = "○";
        hardwareStatus.innerText = "Connecting to Database...";
        loginRiskScore.className = "login-risk-score";
        loginRiskScore.innerText = "Risk Score: Analyzing...";

        try {
            // 2. Send live request to Arush's Backend
            const response = await fetch("http://127.0.0.1:8000/api/users/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username: username, password: password })
            });

            const result = await response.json();

            // 3. Update UI based on Database response
            if (result.status === "success") {
                deviceCheck.className = "check-icon verified";
                deviceCheck.innerText = "✓";
                locationCheck.className = "check-icon verified";
                locationCheck.innerText = "✓";
                hardwareCheck.className = "check-icon verified";
                hardwareCheck.innerText = "✓";
                hardwareStatus.innerText = "Not required for standard login";
                
                loginRiskScore.classList.add("safe");
                loginRiskScore.innerText = "Risk Score: 10 / 100 (Safe)";
                statusTitle.innerText = "✓ Login approved";
                statusMessage.innerText = "Credentials verified.";

                // Save real user ID for backend tracking
                localStorage.setItem("cyberforge_live_user_id", result.user_id);

                setTimeout(function () {
                    window.location.href = "dashboard.html";
                }, 1000);
            } else {
                // Wrong password
                deviceCheck.className = "check-icon warning";
                deviceCheck.innerText = "!";
                locationCheck.className = "check-icon warning";
                locationCheck.innerText = "!";
                
                loginRiskScore.classList.add("high-risk");
                loginRiskScore.innerText = "Risk Score: 100 / 100 (Blocked)";
                
                statusTitle.innerText = "✕ Login blocked";
                statusMessage.innerText = "Invalid username or password.";
                loginButton.disabled = false;
                loginButton.innerText = "Sign in securely";
            }
        } catch (error) {
            console.error(error);
            statusTitle.innerText = "✕ Connection Error";
            statusMessage.innerText = "Cannot reach the FastAPI server.";
            loginButton.disabled = false;
            loginButton.innerText = "Sign in securely";
        }
    });
}


// ========================================
// 2. LIVE TRANSFER SECURITY (FASTAPI)
// ========================================

const sendMoneyButton = document.getElementById("sendMoneyButton");

if (sendMoneyButton) {
    sendMoneyButton.addEventListener("click", async function () {
        const recipient = document.getElementById("recipient").value.trim();
        const amount = Number(document.getElementById("amount").value);

        const transferSecurity = document.getElementById("transferSecurity");
        const transferTitle = document.getElementById("transferStatusTitle");
        const transferMessage = document.getElementById("transferStatusMessage");
        const riskScoreElement = document.getElementById("riskScore");
        const transactionResult = document.getElementById("transactionResult");
        const resultTitle = document.getElementById("resultTitle");
        const resultMessage = document.getElementById("resultMessage");
        const deviceCheck = document.getElementById("transferDeviceCheck");
        const riskCheck = document.getElementById("transferRiskCheck");
        const hardwareCheck = document.getElementById("transferHardwareCheck");
        const hardwareStatus = document.getElementById("transferHardwareStatus");

        if (recipient === "" || !amount || amount <= 0) {
            alert("Please enter a valid recipient and amount.");
            return;
        }

        // 1. Set UI to Loading State
        transferSecurity.classList.remove("hidden");
        transactionResult.classList.add("hidden");
        sendMoneyButton.disabled = true;
        sendMoneyButton.innerText = "Security check running...";

        transferTitle.innerText = "Analyzing transaction risk...";
        transferMessage.innerText = "Sending data to AI Engine...";
        
        deviceCheck.className = "transfer-check-icon checking";
        deviceCheck.innerText = "◉";
        riskCheck.className = "transfer-check-icon checking";
        riskCheck.innerText = "◉";
        hardwareCheck.className = "transfer-check-icon pending";
        hardwareCheck.innerText = "○";
        hardwareStatus.innerText = "Waiting for risk decision";
        
        riskScoreElement.className = "cf-risk-score";
        riskScoreElement.innerText = "Risk Score: Analyzing...";

        // 2. Grab real user ID and format payload
        const currentUserId = localStorage.getItem("cyberforge_live_user_id") || 101;
        const transactionData = {
            user_id: parseInt(currentUserId),
            amount: amount,
            recipient: recipient,
            device_info: navigator.userAgent,
            location_ip: "127.0.0.1"
        };

        try {
            // 3. Send to Arush's Backend
            const response = await fetch("http://127.0.0.1:8000/api/transactions/transfer", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(transactionData)
            });

            const result = await response.json();
            
            deviceCheck.className = "transfer-check-icon verified";
            deviceCheck.innerText = "✓";
            riskCheck.className = "transfer-check-icon verified";
            riskCheck.innerText = "✓";
            riskScoreElement.innerText = "Risk Score: " + result.risk_score + " / 100";

            // 4. Handle Backend AI Decision
            if (result.action === "ALLOW") {
                riskScoreElement.classList.add("safe");
                hardwareCheck.className = "transfer-check-icon verified";
                hardwareCheck.innerText = "✓";
                hardwareStatus.innerText = "Hardware authentication not required";
                
                transferTitle.innerText = "✓ Transaction approved";
                transferMessage.innerText = "Security checks passed.";

                setTimeout(() => {
                    completeTransaction(recipient, amount, transactionResult, resultTitle, resultMessage);
                }, 1200);
            } 
            else if (result.action === "REQUIRE_OTP") {
                riskScoreElement.classList.add("high-risk");
                riskCheck.className = "transfer-check-icon warning";
                riskCheck.innerText = "!";
                
                transferTitle.innerText = "⚠ Verification required";
                transferMessage.innerText = "Medium Risk. OTP Required (Divyank's Module).";
                alert("Backend requested OTP! (Phase 3)");
                sendMoneyButton.disabled = false;
                sendMoneyButton.innerText = "Continue securely";
            } 
            else if (result.action === "REQUIRE_HARDWARE_AUTH") {
                riskScoreElement.classList.add("high-risk");
                riskCheck.className = "transfer-check-icon warning";
                riskCheck.innerText = "!";
                hardwareCheck.className = "transfer-check-icon warning";
                hardwareCheck.innerText = "!";
                hardwareStatus.innerText = "ESP32 verification required";
                
                transferTitle.innerText = "🔐 ESP32 verification";
                transferMessage.innerText = "High Risk. Waiting for secure hardware approval...";
                alert("Backend blocked transaction! Waiting for ESP32 (Sajid's Module).");
            }
        } catch (error) {
            console.error(error);
            transferTitle.innerText = "✕ Server Offline";
            transferMessage.innerText = "Could not connect to FastAPI database.";
            sendMoneyButton.disabled = false;
            sendMoneyButton.innerText = "Continue securely";
        }
    });
}


// ========================================
// COMPLETE TRANSACTION
// ========================================

function completeTransaction(
    recipient,
    amount,
    transactionResult,
    resultTitle,
    resultMessage
) {

    const transferSecurity =
        document.getElementById(
            "transferSecurity"
        );


    transferSecurity.classList.add(
        "hidden"
    );

    transactionResult.classList.remove(
        "hidden"
    );


    resultTitle.innerText =
        "Transaction Complete";


    resultMessage.innerText =
        "₹" +
        amount.toLocaleString("en-IN") +
        " sent successfully to " +
        recipient +
        ".";


    saveTransaction(
        recipient,
        amount,
        "Completed"
    );


    if (sendMoneyButton) {

        sendMoneyButton.disabled =
            false;

        sendMoneyButton.innerText =
            "Continue securely";
    }
}


// ========================================
// 3. LIVE DASHBOARD TRANSACTIONS (FASTAPI)
// ========================================

async function loadDashboardTransactions() {
    const transactionList = document.getElementById("transactionList");

    if (!transactionList) {
        return;
    }

    const currentUserId = localStorage.getItem("cyberforge_live_user_id") || 101;

    try {
        const response = await fetch(`http://127.0.0.1:8000/api/transactions/recent/${currentUserId}`);
        const transactions = await response.json();

        transactionList.innerHTML = "";

        if (transactions.length === 0) {
            transactionList.innerHTML = `
                <p style="color:#858e9a; padding:15px 0;">
                    No transactions yet.
                </p>
            `;
            return;
        }

        transactions.forEach(function (tx) {
            const item = document.createElement("div");
            item.className = "transaction";

            // Match Arush's database schema: tx.recipient_account
            const recipientName = tx.recipient_account || "Unknown";
            const firstLetter = recipientName.charAt(0).toUpperCase();
            
            // Format MySQL timestamp
            const dateObj = new Date(tx.timestamp);
            const formattedDate = dateObj.toLocaleString("en-IN");

            item.innerHTML = `
                <div class="transaction-icon">
                    ${firstLetter}
                </div>
                <div class="transaction-info">
                    <h3>${recipientName}</h3>
                    <p>${formattedDate} • ${tx.status}</p>
                </div>
                <strong>
                    − ₹${tx.amount.toLocaleString("en-IN")}
                </strong>
            `;

            transactionList.appendChild(item);
        });

    } catch (error) {
        console.error("Failed to fetch dashboard data:", error);
        transactionList.innerHTML = `
            <p style="color:#ff7474; padding:15px 0;">
                Failed to load transactions. Is the backend running?
            </p>
        `;
    }
}

loadDashboardTransactions();


// ========================================
// DASHBOARD SEARCH
// ========================================

const searchInput =
    document.querySelector(
        ".cf-search input"
    );


if (searchInput) {

    searchInput.addEventListener(
        "keydown",
        function (event) {

            if (event.key !== "Enter") {
                return;
            }


            const query =
                searchInput.value.trim();


            if (query === "") {

                showFeature(
                    "Search",
                    "Type a person, business, bill or payment service to search."
                );

                return;
            }


            showFeature(
                "Search results",
                'Searching CyberForge for "' +
                query +
                '".'
            );

        }
    );
}


// ========================================
// QR BUTTON
// ========================================

const qrButton =
    document.querySelector(
        ".qr-button"
    );


if (qrButton) {

    qrButton.addEventListener(
        "click",
        function () {

            showFeature(
                "Scan QR",
                "QR scanner demo opened. In the final version this will use your camera to scan UPI/payment QR codes."
            );

        }
    );
}


// ========================================
// QUICK ACTIONS
// ========================================

const quickActions =
    document.querySelectorAll(
        ".quick-action"
    );


quickActions.forEach(function (action) {

    const text =
        action.innerText
            .toLowerCase();


    action.onclick = function () {

        if (text.includes("scan")) {

            showFeature(
                "Scan QR",
                "QR scanner demo is ready. Camera-based scanning can be connected later."
            );

            return;
        }


        if (text.includes("pay")) {

            window.location.href =
                "transfer.html";

            return;
        }


        if (text.includes("bank")) {

            showBankTransfer();

            return;
        }


        if (text.includes("recharge")) {

            showRecharge();

            return;
        }

    };

});


// ========================================
// FEATURE CHIPS
// ========================================

const featureChips =
    document.querySelectorAll(
        ".feature-chip"
    );


featureChips.forEach(function (chip) {

    const text =
        chip.innerText
            .toLowerCase();


    chip.onclick = function () {

        if (text.includes("tap")) {

            showFeature(
                "Tap & Pay",
                "Tap & Pay is ready in demo mode. Your NFC payment feature can be connected when the hardware/backend is ready."
            );

            return;
        }


        if (text.includes("upi")) {

            showFeature(
                "UPI Lite",
                "UPI Lite demo opened. You can use this section for small-value instant payments."
            );

            return;
        }


        if (text.includes("reward")) {

            showRewards();

            return;
        }


        if (text.includes("offer")) {

            showOffers();

            return;
        }

    };

});


// ========================================
// PEOPLE
// ========================================

const people =
    document.querySelectorAll(
        ".person"
    );


people.forEach(function (person) {

    person.onclick = function () {

        const name =
            person.querySelector("p");

        if (!name) {
            return;
        }


        const personName =
            name.innerText;


        if (
            personName.toLowerCase() ===
            "more"
        ) {

            showFeature(
                "People",
                "Your saved contacts will appear here."
            );

            return;
        }


        window.location.href =
            "transfer.html";


        localStorage.setItem(
            "cyberforge_selected_recipient",
            personName
        );

    };

});


// ========================================
// BUSINESS
// ========================================

const businesses =
    document.querySelectorAll(
        ".business"
    );


businesses.forEach(function (business) {

    business.onclick = function () {

        const name =
            business.querySelector("p");


        if (!name) {
            return;
        }


        const businessName =
            name.innerText;


        if (
            businessName.toLowerCase() ===
            "more"
        ) {

            showFeature(
                "Businesses",
                "More CyberForge partner businesses will appear here."
            );

            return;
        }


        showFeature(
            businessName,
            "Payment page opened for " +
            businessName +
            "."
        );

    };

});


// ========================================
// BILLS AND RECHARGES
// ========================================

const billItems =
    document.querySelectorAll(
        ".business"
    );


billItems.forEach(function (item) {

    const billLogo =
        item.querySelector(
            ".bill-logo"
        );


    if (!billLogo) {
        return;
    }


    item.onclick = function () {

        const name =
            item.querySelector("p");


        if (!name) {
            return;
        }


        const service =
            name.innerText;


        if (
            service.toLowerCase() ===
            "more"
        ) {

            showRecharge();

            return;
        }


        showFeature(
            service,
            "Bill payment for " +
            service +
            " is ready in demo mode."
        );

    };

});


// ========================================
// SECURITY BANNER
// ========================================

const securityBannerButton =
    document.querySelector(
        ".security-banner button"
    );


if (securityBannerButton) {

    securityBannerButton.onclick =
        function () {

            showFeature(
                "CyberForge Security",
                "CyberForge analyzes login and payment risk. High-risk actions can require ESP32 hardware authentication, while medium-risk actions require OTP verification."
            );

        };
}


// ========================================
// BALANCE CARD
// ========================================

const balanceCard =
    document.querySelector(
        ".cf-balance"
    );


if (balanceCard) {

    balanceCard.onclick =
        function () {

            showFeature(
                "Secure Account",
                "Available balance: ₹50,000.00\n\nYour account is protected by CyberForge security."
            );

        };
}


// ========================================
// OFFER CARD
// ========================================

const offerCard =
    document.querySelector(
        ".offer-card"
    );


if (offerCard) {

    offerCard.onclick =
        function () {

            showOffers();

        };
}


// ========================================
// SECTION LINKS
// ========================================

const sectionLinks =
    document.querySelectorAll(
        ".section-title span"
    );


sectionLinks.forEach(function (link) {

    link.style.cursor = "pointer";


    link.onclick = function () {

        const text =
            link.innerText
                .toLowerCase();


        if (text.includes("view all")) {

            showAllTransactions();

            return;
        }


        if (text.includes("explore")) {

            showFeature(
                "Businesses",
                "Explore CyberForge partner businesses and pay securely."
            );

            return;
        }


        if (text.includes("manage")) {

            showRecharge();

            return;
        }

    };

});


// ========================================
// BOTTOM NAVIGATION
// ========================================

const navItems =
    document.querySelectorAll(
        ".cf-nav"
    );


navItems.forEach(function (nav) {

    nav.onclick = function () {

        const text =
            nav.innerText
                .toLowerCase();


        if (text.includes("home")) {

            window.location.href =
                "dashboard.html";

            return;
        }


        if (text.includes("money")) {

            window.location.href =
                "transfer.html";

            return;
        }


        if (text.includes("activity")) {

            showAllTransactions();

            return;
        }


        if (text.includes("you")) {

            showProfile();

            return;
        }

    };

});


// ========================================
// PROFILE
// ========================================

const profile =
    document.querySelector(
        ".cf-profile"
    );


if (profile) {

    profile.onclick =
        function () {

            showProfile();

        };
}


function showProfile() {

    const transactions =
        getTransactions();


    showMessage(
        "CyberForge Profile",
        "User: Neeraj\n\nSecurity: Protected\nRisk Engine: Active\nHardware Authentication: Enabled\nTransactions: " +
        transactions.length,
        "Close"
    );

}


// ========================================
// BANK TRANSFER
// ========================================

function showBankTransfer() {

    const modal =
        createFormModal(
            "Bank Transfer",
            `
                <input
                    id="bankName"
                    class="cf-modal-input"
                    placeholder="Bank name"
                >

                <input
                    id="accountNumber"
                    class="cf-modal-input"
                    placeholder="Account number"
                >

                <input
                    id="bankAmount"
                    class="cf-modal-input"
                    type="number"
                    placeholder="Amount"
                >

                <button
                    id="bankTransferButton"
                    class="cf-modal-action"
                >
                    Continue Securely
                </button>
            `
        );


    modal
        .querySelector("#bankTransferButton")
        .onclick = function () {

            const bank =
                modal.querySelector(
                    "#bankName"
                ).value.trim();

            const account =
                modal.querySelector(
                    "#accountNumber"
                ).value.trim();

            const amount =
                Number(
                    modal.querySelector(
                        "#bankAmount"
                    ).value
                );


            if (!bank || !account || !amount) {

                alert(
                    "Please fill all bank transfer details."
                );

                return;
            }


            saveTransaction(
                "Bank - " + account,
                amount
            );


            closeModal();


            showMessage(
                "Bank Transfer Complete",
                "₹" +
                amount.toLocaleString("en-IN") +
                " transfer to " +
                bank +
                " has been completed in demo mode."
            );


            loadDashboardTransactions();

        };

}


// ========================================
// MOBILE RECHARGE
// ========================================

function showRecharge() {

    const modal =
        createFormModal(
            "Mobile Recharge",
            `
                <input
                    id="mobileNumber"
                    class="cf-modal-input"
                    placeholder="Mobile number"
                    maxlength="10"
                >

                <input
                    id="rechargeAmount"
                    class="cf-modal-input"
                    type="number"
                    placeholder="Recharge amount"
                >

                <button
                    id="rechargeButton"
                    class="cf-modal-action"
                >
                    Recharge Securely
                </button>
            `
        );


    modal
        .querySelector("#rechargeButton")
        .onclick = function () {

            const mobile =
                modal.querySelector(
                    "#mobileNumber"
                ).value.trim();

            const amount =
                Number(
                    modal.querySelector(
                        "#rechargeAmount"
                    ).value
                );


            if (
                mobile.length !== 10 ||
                !amount
            ) {

                alert(
                    "Enter a valid 10-digit mobile number and amount."
                );

                return;
            }


            saveTransaction(
                "Mobile Recharge",
                amount
            );


            closeModal();


            showMessage(
                "Recharge Successful",
                "₹" +
                amount.toLocaleString("en-IN") +
                " mobile recharge completed successfully in demo mode."
            );


            loadDashboardTransactions();

        };

}


// ========================================
// REWARDS
// ========================================

function showRewards() {

    showMessage(
        "CyberForge Rewards",
        "You currently have 1,250 CyberForge reward points.\n\nUse them for future cashback and offers.",
        "View Rewards"
    );

}


// ========================================
// OFFERS
// ========================================

function showOffers() {

    showMessage(
        "Exclusive Offers",
        "🎁 10% cashback on selected payments\n\n⚡ Extra rewards on secure transactions\n\n🏷️ Partner discounts available",
        "Explore"
    );

}


// ========================================
// ALL TRANSACTIONS
// ========================================

function showAllTransactions() {

    const transactions =
        getTransactions();


    if (transactions.length === 0) {

        showMessage(
            "Activity",
            "No transactions have been made yet.",
            "Close"
        );

        return;
    }


    let text =
        "Recent CyberForge Activity:\n\n";


    transactions.forEach(
        function (transaction, index) {

            text +=
                (index + 1) +
                ". " +
                transaction.recipient +
                " — ₹" +
                transaction.amount.toLocaleString("en-IN") +
                "\n" +
                transaction.status +
                " • " +
                transaction.date +
                "\n\n";

        }
    );


    showMessage(
        "Activity",
        text,
        "Close"
    );

}


// ========================================
// CREATE FORM MODAL
// ========================================

function createFormModal(
    title,
    content
) {

    let modal =
        document.getElementById(
            "cyberforgeModal"
        );


    if (modal) {
        modal.remove();
    }


    modal =
        document.createElement("div");


    modal.id =
        "cyberforgeModal";


    modal.innerHTML = `

        <div class="cf-modal-box">

            <button class="cf-modal-close">
                ×
            </button>

            <div class="cf-modal-icon">
                🔐
            </div>

            <h2>
                ${title}
            </h2>

            ${content}

        </div>
    `;


    document.body.appendChild(
        modal
    );


    addModalStyles();


    modal.classList.add(
        "show"
    );


    modal
        .querySelector(
            ".cf-modal-close"
        )
        .onclick =
        closeModal;


    return modal;
}


// ========================================
// SELECTED PERSON
// ========================================

const selectedRecipient =
    localStorage.getItem(
        "cyberforge_selected_recipient"
    );


const recipientInput =
    document.getElementById(
        "recipient"
    );


if (
    recipientInput &&
    selectedRecipient
) {

    recipientInput.value =
        selectedRecipient;


    localStorage.removeItem(
        "cyberforge_selected_recipient"
    );

}


// ========================================
// ESCAPE KEY
// ========================================

document.addEventListener(
    "keydown",
    function (event) {

        if (event.key === "Escape") {

            closeModal();

        }

    }
);


// ========================================
// FINISH
// ========================================

console.log(
    "CyberForge frontend loaded successfully."
);