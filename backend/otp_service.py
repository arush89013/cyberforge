
import random
import os
import threading
import requests as http_requests
from dotenv import load_dotenv

load_dotenv()

# EmailJS configuration (set these in .env or Render environment variables)
EMAILJS_SERVICE_ID = os.getenv("EMAILJS_SERVICE_ID", "")
EMAILJS_TEMPLATE_ID = os.getenv("EMAILJS_TEMPLATE_ID", "")
EMAILJS_PUBLIC_KEY = os.getenv("EMAILJS_PUBLIC_KEY", "")
EMAILJS_PRIVATE_KEY = os.getenv("EMAILJS_PRIVATE_KEY", "")  # Optional, for extra security

EMAILJS_API_URL = "https://api.emailjs.com/api/v1.0/email/send"


def generate_otp() -> str:
    return str(random.randint(100000, 999999))


def _send_email_worker(to_email: str, otp_code: str, amount: float, recipient: str):
    try:
        payload = {
            "service_id": EMAILJS_SERVICE_ID,
            "template_id": EMAILJS_TEMPLATE_ID,
            "user_id": EMAILJS_PUBLIC_KEY,
            "template_params": {
                "to_email": to_email,
                "otp_code": otp_code,
                "amount": f"{amount:,.2f}",
                "recipient": recipient,
            }
        }

        # Add private key if configured (recommended for server-side calls)
        if EMAILJS_PRIVATE_KEY:
            payload["accessToken"] = EMAILJS_PRIVATE_KEY

        response = http_requests.post(
            EMAILJS_API_URL,
            json=payload,
            timeout=15
        )

        if response.status_code == 200:
            print(f"[OTP SERVICE] Email sent successfully to {to_email} via EmailJS")
        else:
            print(f"[OTP SERVICE] EmailJS error (HTTP {response.status_code}): {response.text}")

    except http_requests.Timeout:
        print(f"[OTP SERVICE] EmailJS request timed out for {to_email}")
    except Exception as e:
        print(f"[OTP SERVICE] Unexpected error sending email: {e}")


def send_otp_email(to_email: str, otp_code: str, amount: float, recipient: str) -> dict:
    if not EMAILJS_SERVICE_ID or not EMAILJS_TEMPLATE_ID or not EMAILJS_PUBLIC_KEY:
        print(f"[OTP SERVICE] EmailJS not configured. OTP for {to_email}: {otp_code}")
        return {
            "success": True,
            "message": f"OTP generated (EmailJS not configured - check server console). Code: {otp_code}"
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
