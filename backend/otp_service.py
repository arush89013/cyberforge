"""
CyberForge OTP Service (Email via Gmail)
========================================
Handles OTP generation and delivery via Gmail SMTP.
"""

import random
import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")


def generate_otp() -> str:
    """Generate a random 6-digit OTP code."""
    return str(random.randint(100000, 999999))


def send_otp_email(to_email: str, otp_code: str, amount: float, recipient: str) -> dict:
    """
    Send an OTP via Gmail SMTP.

    Returns:
        {"success": True/False, "message": "..."}
    """
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        print(f"[OTP SERVICE] No Gmail credentials configured. OTP for {to_email}: {otp_code}")
        return {
            "success": True,
            "message": f"OTP generated (Gmail credentials not set - check server console). Code: {otp_code}"
        }

    try:
        msg = EmailMessage()
        msg['Subject'] = 'CyberForge Security: Your OTP for Transaction'
        msg['From'] = f"CyberForge Security <{GMAIL_ADDRESS}>"
        msg['To'] = to_email

        body = f"""
Dear User,

A transaction of ₹{amount:,.2f} to {recipient} has been initiated from your account.

Your One-Time Password (OTP) to authorize this transaction is:
{otp_code}

This OTP is valid for 5 minutes. Do not share this code with anyone.

If you did not initiate this transaction, please contact CyberForge Support immediately.

Stay Secure,
The CyberForge AI Guard
        """
        msg.set_content(body)

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            smtp.send_message(msg)

        print(f"[OTP SERVICE] Email sent successfully to {to_email}")
        return {"success": True, "message": "OTP sent successfully to your email"}

    except Exception as e:
        print(f"[OTP SERVICE] Error sending email: {e}")
        return {"success": False, "message": f"Email service error: {str(e)}"}
