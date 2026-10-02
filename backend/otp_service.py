"""
CyberForge OTP Service (Email via Gmail)
========================================
Handles OTP generation and delivery via Gmail SMTP.
Sends emails in a background thread so API responses are instant.
"""

import random
import os
import smtplib
import threading
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")

# SMTP connection timeout in seconds
SMTP_TIMEOUT = 10


def generate_otp() -> str:
    """Generate a random 6-digit OTP code."""
    return str(random.randint(100000, 999999))


def _send_email_worker(to_email: str, otp_code: str, amount: float, recipient: str):
    """
    Internal worker that runs in a background thread.
    Handles the actual SMTP connection and email delivery.
    """
    try:
        msg = EmailMessage()
        msg['Subject'] = 'CyberForge Security: Your OTP for Transaction'
        msg['From'] = f"CyberForge Security <{GMAIL_ADDRESS}>"
        msg['To'] = to_email

        body = f"""
Dear User,

A transaction of Rs.{amount:,.2f} to {recipient} has been initiated from your account.

Your One-Time Password (OTP) to authorize this transaction is:

    {otp_code}

This OTP is valid for 5 minutes. Do not share this code with anyone.

If you did not initiate this transaction, please contact CyberForge Support immediately.

Stay Secure,
The CyberForge AI Guard
        """
        msg.set_content(body)

        with smtplib.SMTP('smtp.gmail.com', 587, timeout=SMTP_TIMEOUT) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            smtp.send_message(msg)

        print(f"[OTP SERVICE] Email sent successfully to {to_email}")

    except smtplib.SMTPAuthenticationError as e:
        print(f"[OTP SERVICE] Gmail authentication failed: {e}")
        print(f"[OTP SERVICE] Check that GMAIL_APP_PASSWORD is a valid App Password (not your Gmail password).")
    except smtplib.SMTPException as e:
        print(f"[OTP SERVICE] SMTP error sending email: {e}")
    except Exception as e:
        print(f"[OTP SERVICE] Unexpected error sending email: {e}")


def send_otp_email(to_email: str, otp_code: str, amount: float, recipient: str) -> dict:
    """
    Send an OTP via Gmail SMTP in a background thread.
    Returns immediately so the API response is not blocked.

    Returns:
        {"success": True/False, "message": "..."}
    """
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        print(f"[OTP SERVICE] No Gmail credentials configured. OTP for {to_email}: {otp_code}")
        return {
            "success": True,
            "message": f"OTP generated (Gmail credentials not set - check server console). Code: {otp_code}"
        }

    # Launch email sending in a background thread so the API responds instantly
    thread = threading.Thread(
        target=_send_email_worker,
        args=(to_email, otp_code, amount, recipient),
        daemon=True
    )
    thread.start()

    print(f"[OTP SERVICE] Email dispatch started in background for {to_email}")
    return {"success": True, "message": "OTP sent successfully to your email"}
