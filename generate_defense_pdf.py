import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        
        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(40, 760, "CyberForge (Banking Sentinel) — Demonstration & Viva Defense Guide")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(40, 752, 572, 752)
            
        # Footer
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(572, 30, page_str)
        self.drawString(40, 30, "CONFIDENTIAL — Academic Evaluation & Defense Preparation")
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(40, 42, 572, 42)
        self.restoreState()

def build_pdf(filename="e:/cyberforge/CyberForge_Demonstration_Defense_Guide.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=50,
        bottomMargin=50
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    primary_color = colors.HexColor("#0F172A")
    accent_blue = colors.HexColor("#1E40AF")
    section_title_color = colors.HexColor("#1E293B")
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=4
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#475569"),
        spaceAfter=15
    )

    h1_style = ParagraphStyle(
        'SecH1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#1E3A8A"),
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )

    q_title_style = ParagraphStyle(
        'QTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#0F172A")
    )

    code_label_style = ParagraphStyle(
        'CodeLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#0369A1")
    )

    code_text_style = ParagraphStyle(
        'CodeText',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#334155")
    )

    ans_label_style = ParagraphStyle(
        'AnsLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#15803D")
    )

    ans_text_style = ParagraphStyle(
        'AnsText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#1E293B")
    )

    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#1E293B")
    )

    table_header_style = ParagraphStyle(
        'TH',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.white
    )

    story = []

    # Title Block
    story.append(Paragraph("CYBERFORGE: BANKING SENTINEL", title_style))
    story.append(Paragraph("Complete Technical Demonstration Defense & Evaluator Q&A Guide", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1E3A8A"), spaceAfter=12))

    # Executive Overview
    overview_text = (
        "<b>Purpose of this Document:</b> This guide provides granular technical answers, mathematical foundations, "
        "and architectural justifications for every potential question an evaluator or professor may ask during the live "
        "demonstration of the CyberForge project. It details the exact code locations and explicitly notes what is natively "
        "implemented versus prototype simulations."
    )
    story.append(Paragraph(overview_text, body_style))
    story.append(Spacer(1, 10))

    def make_qa_box(q_num, question, code_context, exact_answer, is_prototype=False):
        badge_color = "#DC2626" if is_prototype else "#2563EB"
        header_text = f"<b>Q{q_num}: {question}</b>"
        
        content = [
            [Paragraph(header_text, q_title_style)],
            [Paragraph(f"<b>Exact Code Reference:</b> {code_context}", code_text_style)],
            [Paragraph(f"<b>Recommended Defense Answer:</b> \"{exact_answer}\"", ans_text_style)]
        ]
        
        t = Table(content, colWidths=[532])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor("#CBD5E1")),
            ('LINEBELOW', (0, 0), (-1, 0), 0.5, colors.HexColor("#E2E8F0")),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        return t

    # SECTION 1
    story.append(Paragraph("1. Authentication & Cryptographic Storage", h1_style))
    story.append(make_qa_box(
        1, "How are you storing passwords securely in the database?",
        "<b>File:</b> <code>auth.py</code> | <b>Function:</b> <code>hash_password()</code><br/>"
        "Uses <b>PBKDF2-HMAC-SHA256</b> with <b>260,000 iterations</b> and a <b>256-bit cryptographically secure random salt</b> (<code>os.urandom(32)</code>). Stored format: <code>iterations$salt_hex$hash_hex</code>.",
        "We use PBKDF2-HMAC-SHA256 compliant with NIST SP 800-132 and OWASP 2023 recommendations. Instead of fast reversible encryption or vulnerable simple hashes like MD5/plain SHA256, we generate an independent 256-bit salt per user and apply 260,000 hashing rounds. This computationally exhausts attackers, making GPU brute-forcing and Rainbow Table dictionary lookups infeasible."
    ))
    story.append(Spacer(1, 8))

    story.append(make_qa_box(
        2, "What happens during login verification? Do you decrypt the stored password?",
        "<b>File:</b> <code>auth.py</code> | <b>Function:</b> <code>verify_password()</code><br/>"
        "Extracts salt & iteration count from stored string, computes PBKDF2 on provided password, and calls <code>hmac.compare_digest()</code>.",
        "No, cryptographic hashes are strictly one-way and mathematically non-reversible. During login, our server extracts the user's specific salt from the database, re-derives the key with the supplied password, and compares the outputs using constant-time comparison (hmac.compare_digest) to prevent timing-based side-channel attacks."
    ))
    story.append(Spacer(1, 8))

    story.append(make_qa_box(
        3, "How is the session managed after login? Are you using JWT or Cookies?",
        "<b>File:</b> <code>script.js</code> (lines 75-80)<br/>"
        "Current frontend stores <code>cf_user_id</code> and <code>cf_username</code> in browser <code>localStorage</code>.",
        "In our current prototype, session identification is managed via client-side local storage for rapid UI state management. In a full enterprise production rollout, this architecture integrates signed short-lived JSON Web Tokens (JWT) coupled with HttpOnly, SameSite=Strict cookies to eliminate Cross-Site Scripting (XSS) token theft.",
        is_prototype=True
    ))
    story.append(Spacer(1, 12))

    # SECTION 2
    story.append(Paragraph("2. Profile & Adaptive Security Configuration", h1_style))
    story.append(make_qa_box(
        4, "Why do you maintain both a 4-Digit PIN and a Login Password?",
        "<b>File:</b> <code>models.py</code> (<code>transaction_pin</code> column) & <code>main.py</code> (line 125)<br/>"
        "PIN is verified only when transaction risk score is < 25 (Low Risk).",
        "We implement Multi-Tier Step-Up Authentication (Risk-Based Authentication). The master password secures account access, while the 4-digit PIN provides a low-friction second factor for familiar, low-risk micro-transactions (analogous to UPI PINs), reserving disruptive OTPs strictly for anomalous behavior."
    ))
    story.append(Spacer(1, 8))

    story.append(make_qa_box(
        5, "How is the registered email protected and validated?",
        "<b>File:</b> <code>main.py</code> (<code>mask_email()</code>) & <code>script.js</code><br/>"
        "RFC 5322 regex validation on input; server masks email string before returning to client (e.g. <code>a***9@gmail.com</code>).",
        "We enforce regex validation at ingestion. Furthermore, under Privacy-by-Design and DPDP/GDPR principles, all API responses and frontend views mask Personally Identifiable Information (PII) so cleartext emails are never displayed on screens or stored in client logs."
    ))
    story.append(Spacer(1, 12))

    # SECTION 3
    story.append(Paragraph("3. Client Telemetry & Behavioral Biometrics", h1_style))
    story.append(make_qa_box(
        6, "How do you capture typing speed? Is this a keylogger?",
        "<b>File:</b> <code>script.js</code> (lines 260-275) | <code>trackKeystroke()</code><br/>"
        "Measures <code>typingSpeedMs = Date.now() - firstKeystrokeTime</code>. Characters are never inspected.",
        "No, this is strictly Privacy-Preserving Behavioral Biometrics. We do NOT capture keystroke characters, which would constitute a severe keylogging vulnerability. We only record the temporal latency (time delta in milliseconds) between initial interaction and submission. This reliably differentiates genuine human typing cadence (1.5s to 8s) from automated bot pastes (< 500ms)."
    ))
    story.append(Spacer(1, 8))

    story.append(make_qa_box(
        7, "How are Client IP and Device fingerprint extracted? Can they be spoofed?",
        "<b>File:</b> <code>main.py</code> (line 79) | <code>request.client.host</code><br/>"
        "Server extracts IP directly from the TCP socket connection, ignoring spoofable client headers.",
        "To prevent client payload manipulation, the client IP is extracted directly at the socket level on the backend via request.client.host. The device fingerprint utilizes navigator.userAgent, and historical familiarity is established by querying past completed transactions for that user in MySQL."
    ))
    story.append(Spacer(1, 12))

    # SECTION 4
    story.append(Paragraph("4. AI Risk Engine & Decision Matrix", h1_style))
    story.append(make_qa_box(
        8, "What exact Machine Learning model is used and how is risk computed?",
        "<b>Files:</b> <code>predictor.py</code> & <code>train_model.py</code><br/>"
        "<b>Model:</b> Scikit-Learn <code>IsolationForest</code> (150 estimators) + 5-factor weighted ensemble + deterministic guardrails.",
        "We employ a Hybrid Ensemble Risk Model. It evaluates a 5-dimensional feature vector: Network IP Context (25%), Device Fingerprint (20%), Typing Cadence vs Baseline (15%), Amount Deviation (25%), and Circadian Time Window (15%). An unsupervised Isolation Forest detects multi-dimensional anomaly clustering. Deterministic Banking Guardrails enforce maximum risk floors (>= 80) if transactions exceed Rs. 50,000 or bot speed is detected."
    ))
    story.append(Spacer(1, 8))

    story.append(make_qa_box(
        9, "Why choose Isolation Forest over Deep Neural Networks (DNN)?",
        "<b>File:</b> <code>train_model.py</code>",
        "1) Unsupervised Anomaly Isolation: Real banking fraud is rare (<0.1%) with constantly evolving zero-day attack patterns; supervised DNNs suffer from severe class imbalance. 2) Real-time Latency: Sub-10ms CPU inference time. 3) Green Computing: Zero GPU compute overhead."
    ))
    story.append(Spacer(1, 8))

    story.append(make_qa_box(
        10, "What are the decision score thresholds and associated actions?",
        "<b>File:</b> <code>main.py</code> (lines 125-165)",
        "Score < 25 (Low Risk): REQUIRE_PIN (frictionless 4-digit PIN). Score 25 to 79 (Medium Risk): REQUIRE_OTP (dispatches 6-digit Email OTP via SMTP). Score >= 80 (High Risk): REQUIRE_HARDWARE_AUTH (locks transfer into ESP32_Awaiting state)."
    ))
    story.append(Spacer(1, 12))

    # SECTION 5
    story.append(Paragraph("5. Out-of-Band OTP Generation & Delivery", h1_style))
    story.append(make_qa_box(
        11, "How are OTPs generated and replay attacks prevented?",
        "<b>Files:</b> <code>otp_service.py</code> & <code>main.py</code> (<code>/api/otp/verify</code>)<br/>"
        "Table: <code>otp_records</code> (fields: <code>otp_code</code>, <code>created_at</code>, <code>is_used</code>).",
        "OTPs are generated on the backend and committed to MySQL. We mitigate replay and brute force attacks through: 1) Single-Use Invalidation: upon successful verification, is_used is immediately flagged True. 2) Time-to-Live: strict 5-minute expiration window. 3) Resend Revocation: generating a new OTP automatically invalidates all previous unused tokens."
    ))
    story.append(Spacer(1, 8))

    story.append(make_qa_box(
        12, "What protocol and encryption are used to send the OTP email?",
        "<b>File:</b> <code>otp_service.py</code> | <code>smtplib.SMTP_SSL('smtp.gmail.com', 465)</code>",
        "We communicate via direct SMTP wrapped in end-to-end Transport Layer Security / SSL over Port 465. Authentication uses Google's 16-character App Password stored in backend environment variables, avoiding cleartext credentials in source control."
    ))
    story.append(Spacer(1, 12))

    # SECTION 6
    story.append(Paragraph("6. Hardware Security Token (ESP32 Integration)", h1_style))
    story.append(make_qa_box(
        13, "How does the hardware authentication work with the ESP32?",
        "<b>File:</b> <code>main.py</code> (<code>/api/hardware/pending_requests</code> & <code>/api/hardware/verify</code>)",
        "When risk is >= 80, the backend sets status to 'ESP32_Awaiting'. The ESP32 IoT microcontroller polls the REST API over Wi-Fi. Upon detecting a pending high-risk transaction, it displays the amount on an OLED screen and requires physical push-button confirmation, posting back an APPROVED payload to complete the transfer.",
        is_prototype=True
    ))
    story.append(Spacer(1, 12))

    # SECTION 7
    story.append(Paragraph("7. Database Architecture & Audit Logging", h1_style))
    story.append(make_qa_box(
        14, "What database is used and how is non-repudiation maintained?",
        "<b>Files:</b> <code>models.py</code> & <code>database.py</code> | MySQL 8.0 with InnoDB engine",
        "We utilize MySQL 8.0 with SQLAlchemy ORM, ensuring full ACID transactional compliance. Non-repudiation and regulatory auditing are guaranteed via the audit_logs table, which writes immutable records containing transaction IDs, calculated risk scores, active anomaly flags, and authorization reasons with UTC timestamps."
    ))
    story.append(Spacer(1, 15))

    # SECTION 8: IMPLEMENTATION MATRIX TABLE
    story.append(Paragraph("8. Implementation Status Matrix (Native vs Prototype)", h1_style))
    story.append(Spacer(1, 4))

    matrix_data = [
        [Paragraph("Feature Component", table_header_style), Paragraph("Implementation Status", table_header_style), Paragraph("Technical Details & Notes", table_header_style)],
        [Paragraph("Password Hashing", body_style), Paragraph("<b>100% Native</b>", body_style), Paragraph("PBKDF2-HMAC-SHA256, 260k iterations, 256-bit salt in auth.py.", body_style)],
        [Paragraph("Email OTP Dispatch", body_style), Paragraph("<b>100% Native</b>", body_style), Paragraph("Real SMTP over SSL (Port 465) via Gmail App Password.", body_style)],
        [Paragraph("Behavioral Biometrics", body_style), Paragraph("<b>100% Native</b>", body_style), Paragraph("DOM keystroke latency timers in milliseconds (Privacy-by-Design).", body_style)],
        [Paragraph("AI Risk Engine", body_style), Paragraph("<b>100% Native</b>", body_style), Paragraph("Isolation Forest + 5-feature baseline scoring + banking guardrails.", body_style)],
        [Paragraph("Relational Persistence", body_style), Paragraph("<b>100% Native</b>", body_style), Paragraph("MySQL 8.0 with SQLAlchemy ORM and audit logging.", body_style)],
        [Paragraph("Hardware Token (ESP32)", body_style), Paragraph("<b>API-Ready</b>", body_style), Paragraph("Endpoints active in main.py; can be verified via REST or physical IoT.", body_style)],
        [Paragraph("Core Banking Core", body_style), Paragraph("<b>Simulated</b>", body_style), Paragraph("Simulated wallet balance for risk engine demonstration.", body_style)]
    ]

    mat_table = Table(matrix_data, colWidths=[130, 110, 292])
    mat_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
    ]))
    story.append(mat_table)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF successfully generated at: {filename}")

if __name__ == "__main__":
    build_pdf()
