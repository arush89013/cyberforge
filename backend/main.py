from fastapi import FastAPI, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import SessionLocal, engine, Base
import models
import schemas
from datetime import datetime, timezone, timedelta
import re
import math
import requests

def get_lat_lon(ip: str):
    if ip in ('127.0.0.1', '::1', 'localhost', 'unknown'): return 28.6139, 77.2090
    try:
        r = requests.get(f'http://ip-api.com/json/{ip}', timeout=1.0)
        if r.json().get('status') == 'success': return r.json()['lat'], r.json()['lon']
    except: pass
    return None, None

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))


from ai_engine.predictor import evaluate_risk
from otp_service import generate_otp, send_otp_email
from auth import hash_password, verify_password, encrypt_email, decrypt_email

# Automatically create tables in MySQL
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Banking Sentinel API")
from fastapi.middleware.cors import CORSMiddleware

# Allow frontend to communicate with the server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OTP expiry duration
OTP_EXPIRY_MINUTES = 5


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def mask_email(email_str: str) -> str:
    if not email_str: return None
    try:
        email = decrypt_email(email_str)
        local, domain = email.split('@')
        if len(local) > 2:
            masked_local = f"{local[0]}{'*' * (len(local) - 2)}{local[-1]}"
        else:
            masked_local = local
        return f"{masked_local}@{domain}"
    except ValueError:
        return email


def compute_user_baselines(db: Session, user_id: int, recipient: str = None) -> dict:
    completed_statuses = ["Completed", "OTP_Awaiting", "ESP32_Awaiting"]

    past_transactions = db.query(models.Transaction).filter(
        models.Transaction.user_id == user_id,
        models.Transaction.status.in_(completed_statuses)
    ).all()

    if not past_transactions:
        return {
            "avg_amount": None,
            "avg_typing_speed": None,
            "tx_count_last_hour": 0,
            "tx_count_last_day": 0,
            "is_known_recipient": False,
            "recipient_tx_count": 0,
        }

    amounts = [tx.amount for tx in past_transactions if tx.amount is not None]
    avg_amount = sum(amounts) / len(amounts) if amounts else None

    typing_speeds = [tx.typing_speed_ms for tx in past_transactions if tx.typing_speed_ms is not None]
    avg_typing_speed = sum(typing_speeds) / len(typing_speeds) if typing_speeds else None

    # Transaction velocity: count recent transactions
    now = datetime.now(timezone.utc)
    one_hour_ago = now - timedelta(hours=1)
    one_day_ago = now - timedelta(hours=24)

    tx_count_last_hour = 0
    tx_count_last_day = 0
    for tx in past_transactions:
        tx_time = tx.timestamp
        if tx_time and tx_time.tzinfo is None:
            tx_time = tx_time.replace(tzinfo=timezone.utc)
        if tx_time and tx_time >= one_hour_ago:
            tx_count_last_hour += 1
        if tx_time and tx_time >= one_day_ago:
            tx_count_last_day += 1

    # Recipient familiarity
    is_known_recipient = False
    recipient_tx_count = 0
    if recipient:
        recipient_lower = recipient.strip().lower()
        for tx in past_transactions:
            if tx.recipient_account and tx.recipient_account.strip().lower() == recipient_lower:
                recipient_tx_count += 1
        is_known_recipient = recipient_tx_count > 0

    return {
        "avg_amount": avg_amount,
        "avg_typing_speed": avg_typing_speed,
        "tx_count_last_hour": tx_count_last_hour,
        "tx_count_last_day": tx_count_last_day,
        "is_known_recipient": is_known_recipient,
        "recipient_tx_count": recipient_tx_count,
    }


@app.post("/api/transactions/transfer")
def initiate_transfer(tx: schemas.TransactionCreate, request: Request, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == tx.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if user.balance < tx.amount:
        return {"action": "INSUFFICIENT_FUNDS", "message": "Insufficient balance for this transaction."}

    forwarded = request.headers.get("X-Forwarded-For")
    client_ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")

    completed_statuses = ["Completed", "OTP_Awaiting", "ESP32_Awaiting"]

    travel_speed_kmh = 0.0
    last_tx = db.query(models.Transaction).filter(models.Transaction.user_id == tx.user_id, models.Transaction.status.in_(completed_statuses)).order_by(models.Transaction.timestamp.desc()).first()
    if last_tx and last_tx.timestamp and last_tx.location_ip and last_tx.location_ip != client_ip:
        lat1, lon1 = get_lat_lon(last_tx.location_ip)
        lat2, lon2 = get_lat_lon(client_ip)
        if lat1 is not None and lon1 is not None and lat2 is not None and lon2 is not None:
            tx_time = last_tx.timestamp if last_tx.timestamp.tzinfo else last_tx.timestamp.replace(tzinfo=timezone.utc)
            time_diff = (datetime.now(timezone.utc) - tx_time).total_seconds() / 3600.0
            if time_diff > 0: travel_speed_kmh = haversine(lat1, lon1, lat2, lon2) / time_diff

    known_ip = db.query(models.Transaction).filter(
        models.Transaction.user_id == tx.user_id,
        models.Transaction.location_ip == client_ip,
        models.Transaction.status.in_(completed_statuses)
    ).first() is not None

    known_device = db.query(models.Transaction).filter(
        models.Transaction.user_id == tx.user_id,
        models.Transaction.device_info == tx.device_info,
        models.Transaction.status.in_(completed_statuses)
    ).first() is not None

    baselines = compute_user_baselines(db, tx.user_id, tx.recipient)
    current_hour = datetime.now(timezone.utc).hour

    transaction_data = {
        "amount":              tx.amount,
        "is_known_ip":         known_ip,
        "is_known_device":     known_device,
        "typing_speed_ms":     tx.typing_speed_ms,
        "avg_typing_speed":    baselines["avg_typing_speed"],
        "avg_amount":          baselines["avg_amount"],
        "current_hour":        current_hour,
        "tx_count_last_hour":  baselines["tx_count_last_hour"],
        "tx_count_last_day":   baselines["tx_count_last_day"],
        "is_known_recipient":  baselines["is_known_recipient"],
        "recipient_tx_count":  baselines["recipient_tx_count"],
        "balance":             user.balance,
        "travel_speed_kmh":    travel_speed_kmh,
    }

    ai_result = evaluate_risk(transaction_data)
    actual_risk_score = ai_result["risk_score"]

    if actual_risk_score < 25:
        user = db.query(models.User).filter(models.User.id == tx.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if not user.transaction_pin:
            return {"action": "REQUIRE_SETUP", "message": "Please set a PIN in your profile first."}

        if not tx.pin:
            return {
                "transaction_id": None,
                "risk_score": actual_risk_score,
                "action": "REQUIRE_PIN",
                "flags": ai_result["flags"],
                "sub_scores": ai_result["sub_scores"],
            }

        if not verify_password(tx.pin, user.transaction_pin):
            return {"action": "INVALID_PIN", "message": "Incorrect PIN entered."}

        # Deduct balance for low-risk PIN-approved transaction
        user.balance -= tx.amount
        final_status = "Completed"
        action = "ALLOW"

    elif actual_risk_score < 80:
        final_status = "OTP_Awaiting"
        action = "REQUIRE_OTP"
    else:
        final_status = "ESP32_Awaiting"
        action = "REQUIRE_HARDWARE_AUTH"

    new_tx = models.Transaction(
        user_id=tx.user_id,
        amount=tx.amount,
        recipient_account=tx.recipient,
        status=final_status,
        device_info=tx.device_info,
        location_ip=client_ip,
        typing_speed_ms=tx.typing_speed_ms,
        risk_score=actual_risk_score,
    )
    db.add(new_tx)
    db.commit()
    db.refresh(new_tx)

    otp_sent = False
    masked_email_str = ""
    
    if action == "REQUIRE_OTP":
        user = db.query(models.User).filter(models.User.id == tx.user_id).first()

        if not user or not user.email_address:
            return {
                "transaction_id": new_tx.id,
                "risk_score": actual_risk_score,
                "action": "REQUIRE_EMAIL_SETUP",
                "message": "Please register your email address in profile settings first.",
                "flags": ai_result["flags"],
                "sub_scores": ai_result["sub_scores"],
            }

        otp_code = generate_otp()
        otp_record = models.OTPRecord(
            user_id=tx.user_id,
            transaction_id=new_tx.id,
            otp_code=otp_code,
        )
        db.add(otp_record)
        db.commit()

        email_result = send_otp_email(decrypt_email(user.email_address), otp_code, tx.amount, tx.recipient)
        otp_sent = email_result["success"]
        masked_email_str = mask_email(user.email_address)

    response = {
        "transaction_id": new_tx.id,
        "risk_score": actual_risk_score,
        "action": action,
        "flags": ai_result["flags"],
        "sub_scores": ai_result["sub_scores"],
    }

    if action == "REQUIRE_OTP" and otp_sent:
        response["masked_email"] = masked_email_str

    return response


@app.post("/api/otp/verify")
def verify_otp(data: schemas.OTPVerify, db: Session = Depends(get_db)):
    otp_record = db.query(models.OTPRecord).filter(
        models.OTPRecord.transaction_id == data.transaction_id,
        models.OTPRecord.is_used == False,
    ).order_by(models.OTPRecord.created_at.desc()).first()

    if not otp_record:
        return {"status": "error", "message": "No OTP found. Please request a new one."}

    now = datetime.now(timezone.utc)
    created_at = otp_record.created_at if otp_record.created_at.tzinfo else otp_record.created_at.replace(tzinfo=timezone.utc)
    otp_age = now - created_at
    if otp_age > timedelta(minutes=OTP_EXPIRY_MINUTES):
        return {"status": "expired", "message": "OTP has expired. Please request a new one."}

    if data.otp != otp_record.otp_code:
        return {"status": "invalid", "message": "Incorrect OTP. Please try again."}

    tx = db.query(models.Transaction).filter(models.Transaction.id == data.transaction_id).first()
    if not tx:
        return {"status": "error", "message": "Transaction not found."}

    if tx.status == "Completed":
        return {"status": "error", "message": "Transaction already completed."}

    user = db.query(models.User).filter(models.User.id == tx.user_id).first()
    if not user or user.balance < tx.amount:
        return {"status": "error", "message": "Insufficient balance."}

    otp_record.is_used = True
    user.balance -= tx.amount
    tx.status = "Completed"
    db.commit()

    return {
        "status": "success",
        "message": "OTP verified! Transaction approved.",
        "transaction_id": data.transaction_id,
    }


@app.post("/api/otp/resend/{transaction_id}")
def resend_otp(transaction_id: int, db: Session = Depends(get_db)):
    tx = db.query(models.Transaction).filter(
        models.Transaction.id == transaction_id,
        models.Transaction.status == "OTP_Awaiting",
    ).first()

    if not tx:
        return {"status": "error", "message": "No pending OTP transaction found."}

    user = db.query(models.User).filter(models.User.id == tx.user_id).first()
    if not user or not user.email_address:
        return {"status": "error", "message": "No email address registered."}

    old_otps = db.query(models.OTPRecord).filter(
        models.OTPRecord.transaction_id == transaction_id,
        models.OTPRecord.is_used == False,
    ).all()
    for old in old_otps:
        old.is_used = True

    otp_code = generate_otp()
    otp_record = models.OTPRecord(
        user_id=tx.user_id,
        transaction_id=transaction_id,
        otp_code=otp_code,
    )
    db.add(otp_record)
    db.commit()

    email_result = send_otp_email(decrypt_email(user.email_address), otp_code, tx.amount, tx.recipient_account)
    masked_email_str = mask_email(user.email_address)

    return {
        "status": "success" if email_result["success"] else "error",
        "message": email_result["message"],
        "masked_email": masked_email_str,
    }


@app.get("/api/hardware/pending_requests")
def check_hardware_requests(user_id: int = 0, db: Session = Depends(get_db)):
    # 1. Look for a pending transaction for this user specifically
    pending = None
    if user_id and user_id > 0:
        pending = db.query(models.Transaction).filter(
            models.Transaction.user_id == user_id,
            models.Transaction.status == "ESP32_Awaiting"
        ).order_by(models.Transaction.timestamp.desc()).first()

    # 2. If no pending transaction for specific user, check for any pending transaction across all users (Demo / Universal Token mode)
    if not pending:
        pending = db.query(models.Transaction).filter(
            models.Transaction.status == "ESP32_Awaiting"
        ).order_by(models.Transaction.timestamp.desc()).first()

    if not pending:
        return {"status": "NO_PENDING_REQUESTS"}

    # Auto-expire pending requests older than 5 minutes
    if pending.timestamp:
        now = datetime.now(timezone.utc)
        tx_time = pending.timestamp if pending.timestamp.tzinfo else pending.timestamp.replace(tzinfo=timezone.utc)
        if (now - tx_time) > timedelta(minutes=5):
            pending.status = "Blocked"
            db.commit()
            return {"status": "NO_PENDING_REQUESTS"}

    return {
        "status": "PENDING_REQUEST",
        "transaction_id": pending.id,
        "amount": pending.amount,
        "recipient": pending.recipient_account
    }


@app.post("/api/hardware/verify")
def verify_hardware(verification: schemas.HardwareVerify, db: Session = Depends(get_db)):
    tx = db.query(models.Transaction).filter(models.Transaction.id == verification.transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if tx.status == "Completed":
        return {"message": f"Transaction {tx.id} is already Completed"}

    if verification.status == "APPROVED":
        user = db.query(models.User).filter(models.User.id == tx.user_id).first()
        if user and user.balance >= tx.amount:
            user.balance -= tx.amount
            tx.status = "Completed"
        else:
            tx.status = "Blocked"
    else:
        tx.status = "Blocked"
        
    db.commit()
    return {"message": f"Transaction {tx.id} updated to {tx.status}"}


@app.post("/api/users/register")
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # Check if username already taken
    existing = db.query(models.User).filter(models.User.username == user.username).first()
    if existing:
        return {"status": "error", "message": "Username already exists."}

    # Hash password with bcrypt (salt + 2^12 rounds) before storing
    hashed_pw = hash_password(user.password)

    new_user = models.User(
        username=user.username,
        password_hash=hashed_pw,
        balance=1000000.0
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"status": "success", "message": f"User {new_user.id} created successfully!"}


@app.post("/api/users/{user_id}/pin")
def update_transaction_pin(user_id: int, pin_data: schemas.PinUpdate, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return {"status": "error", "message": "User not found"}
    user.transaction_pin = hash_password(pin_data.pin)
    db.commit()
    return {"status": "success", "message": "PIN securely updated!"}


@app.post("/api/users/{user_id}/email")
def update_email_address(user_id: int, email_data: schemas.EmailUpdate, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return {"status": "error", "message": "User not found"}

    email = email_data.email.strip()
    # Simple regex for email validation
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return {"status": "error", "message": "Invalid email address format."}

    user.email_address = encrypt_email(email)
    db.commit()

    return {"status": "success", "message": f"Email address {mask_email(user.email_address)} registered successfully!"}


@app.get("/api/users/{user_id}/profile")
def get_user_profile(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return {"status": "error", "message": "User not found"}

    return {
        "user_id": user.id,
        "username": user.username,
        "balance": user.balance,
        "has_pin": bool(user.transaction_pin),
        "has_email": bool(user.email_address),
        "masked_email": mask_email(user.email_address) if user.email_address else None,
    }


@app.post("/api/users/login")
def login(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()

    if not db_user:
        return {"status": "error", "message": "Invalid username or password"}

    stored = db_user.password_hash

    # Detect if the stored password is a PBKDF2 hash (format: "iterations$salt$hash")
    # or legacy plaintext. PBKDF2 hashes always have exactly 2 '$' delimiters.
    parts = stored.split("$") if stored else []
    is_hashed = (len(parts) == 3 and parts[0].isdigit())

    if is_hashed:
        # PBKDF2-HMAC-SHA256 verification
        password_valid = verify_password(user.password, stored)
    else:
        # Legacy plaintext fallback for old accounts created before hash upgrade.
        # On successful legacy login, auto-upgrade the hash to PBKDF2.
        password_valid = (user.password == stored)
        if password_valid:
            db_user.password_hash = hash_password(user.password)
            db.commit()

    if not password_valid:
        return {"status": "error", "message": "Invalid username or password"}

    return {"status": "success", "user_id": db_user.id, "username": db_user.username}


@app.get("/api/transactions/recent/{user_id}")
def get_recent_transactions(user_id: int, db: Session = Depends(get_db)):
    return db.query(models.Transaction).filter(
        models.Transaction.user_id == user_id,
        models.Transaction.status.notin_(["OTP_Awaiting", "ESP32_Awaiting"])
    ).order_by(models.Transaction.timestamp.desc()).limit(10).all()

@app.post("/api/transactions/cancel/{transaction_id}")
def cancel_transaction(transaction_id: int, db: Session = Depends(get_db)):
    tx = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if tx and tx.status in ["OTP_Awaiting", "ESP32_Awaiting"]:
        tx.status = "Cancelled"
        db.commit()
        return {"status": "success"}
    return {"status": "error", "message": "Cannot cancel this transaction"}


@app.get("/api/transactions/status/{transaction_id}")
def get_transaction_status(transaction_id: int, db: Session = Depends(get_db)):
    tx = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if not tx:
        return {"status": "NOT_FOUND"}
    return {"status": tx.status, "transaction_id": tx.id}


#                 cd backend
#                 .\venv\Scripts\Activate
#                 uvicorn main:app --reload

@app.delete("/api/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Delete related records
    db.query(models.OTPRecord).filter(models.OTPRecord.user_id == user_id).delete()
    db.query(models.Transaction).filter(models.Transaction.user_id == user_id).delete()
    
    db.delete(user)
    db.commit()
    return {"status": "success", "message": "User deleted successfully"}
