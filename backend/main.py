from fastapi import FastAPI, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import SessionLocal, engine, Base
import models
import schemas
from datetime import datetime, timezone, timedelta
import re

from ai_engine.predictor import evaluate_risk
from otp_service import generate_otp, send_otp_email

# Automatically create tables in MySQL
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Banking Sentinel API")
from fastapi.middleware.cors import CORSMiddleware

# Allow frontend to communicate with the server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
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


def mask_email(email: str) -> str:
    """Masks an email address (e.g., test@example.com -> t**t@example.com)."""
    try:
        local, domain = email.split('@')
        if len(local) > 2:
            masked_local = f"{local[0]}{'*' * (len(local) - 2)}{local[-1]}"
        else:
            masked_local = local
        return f"{masked_local}@{domain}"
    except ValueError:
        return email


# ============================================================
# HELPER: Compute user behavioral baselines from history
# ============================================================
def compute_user_baselines(db: Session, user_id: int) -> dict:
    completed_statuses = ["Completed", "OTP_Awaiting", "ESP32_Awaiting"]

    past_transactions = db.query(models.Transaction).filter(
        models.Transaction.user_id == user_id,
        models.Transaction.status.in_(completed_statuses)
    ).all()

    if not past_transactions:
        return {"avg_amount": None, "avg_typing_speed": None}

    amounts = [tx.amount for tx in past_transactions if tx.amount is not None]
    avg_amount = sum(amounts) / len(amounts) if amounts else None

    typing_speeds = [tx.typing_speed_ms for tx in past_transactions if tx.typing_speed_ms is not None]
    avg_typing_speed = sum(typing_speeds) / len(typing_speeds) if typing_speeds else None

    return {
        "avg_amount": avg_amount,
        "avg_typing_speed": avg_typing_speed,
    }


# ============================================================
# TRANSFER — Core transaction endpoint
# ============================================================
@app.post("/api/transactions/transfer")
def initiate_transfer(tx: schemas.TransactionCreate, request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"

    completed_statuses = ["Completed", "OTP_Awaiting", "ESP32_Awaiting"]

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

    baselines = compute_user_baselines(db, tx.user_id)
    current_hour = datetime.now(timezone.utc).hour

    transaction_data = {
        "amount":           tx.amount,
        "is_known_ip":      known_ip,
        "is_known_device":  known_device,
        "typing_speed_ms":  tx.typing_speed_ms,
        "avg_typing_speed": baselines["avg_typing_speed"],
        "avg_amount":       baselines["avg_amount"],
        "current_hour":     current_hour,
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

        if tx.pin != user.transaction_pin:
            return {"action": "INVALID_PIN", "message": "Incorrect PIN entered."}

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

        email_result = send_otp_email(user.email_address, otp_code, tx.amount, tx.recipient)
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


# ============================================================
# OTP — Verify submitted OTP
# ============================================================
@app.post("/api/otp/verify")
def verify_otp(data: schemas.OTPVerify, db: Session = Depends(get_db)):
    otp_record = db.query(models.OTPRecord).filter(
        models.OTPRecord.transaction_id == data.transaction_id,
        models.OTPRecord.is_used == False,
    ).order_by(models.OTPRecord.created_at.desc()).first()

    if not otp_record:
        return {"status": "error", "message": "No OTP found. Please request a new one."}

    now = datetime.now(timezone.utc)
    otp_age = now - otp_record.created_at.replace(tzinfo=timezone.utc)
    if otp_age > timedelta(minutes=OTP_EXPIRY_MINUTES):
        return {"status": "expired", "message": "OTP has expired. Please request a new one."}

    if data.otp != otp_record.otp_code:
        return {"status": "invalid", "message": "Incorrect OTP. Please try again."}

    otp_record.is_used = True

    tx = db.query(models.Transaction).filter(models.Transaction.id == data.transaction_id).first()
    if tx:
        tx.status = "Completed"

    db.commit()

    return {
        "status": "success",
        "message": "OTP verified! Transaction approved.",
        "transaction_id": data.transaction_id,
    }


# ============================================================
# OTP — Resend OTP for a pending transaction
# ============================================================
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

    email_result = send_otp_email(user.email_address, otp_code, tx.amount, tx.recipient_account)
    masked_email_str = mask_email(user.email_address)

    return {
        "status": "success" if email_result["success"] else "error",
        "message": email_result["message"],
        "masked_email": masked_email_str,
    }


# ============================================================
# HARDWARE — ESP32 polling & verification
# ============================================================
@app.get("/api/hardware/pending_requests")
def check_hardware_requests(user_id: int, db: Session = Depends(get_db)):
    pending = db.query(models.Transaction).filter(
        models.Transaction.user_id == user_id,
        models.Transaction.status == "ESP32_Awaiting"
    ).first()

    if not pending:
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

    tx.status = "Completed" if verification.status == "APPROVED" else "Blocked"
    db.commit()
    return {"message": f"Transaction {tx.id} updated to {tx.status}"}


# ============================================================
# USER — Registration, login, PIN & Email management
# ============================================================
@app.post("/api/users/register")
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    new_user = models.User(username=user.username, password_hash=user.password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": f"User {new_user.id} created successfully!"}


@app.post("/api/users/{user_id}/pin")
def update_transaction_pin(user_id: int, pin_data: schemas.PinUpdate, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return {"status": "error", "message": "User not found"}
    user.transaction_pin = pin_data.pin
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

    user.email_address = email
    db.commit()

    return {"status": "success", "message": f"Email address {mask_email(email)} registered successfully!"}


@app.get("/api/users/{user_id}/profile")
def get_user_profile(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return {"status": "error", "message": "User not found"}

    return {
        "user_id": user.id,
        "username": user.username,
        "has_pin": bool(user.transaction_pin),
        "has_email": bool(user.email_address),
        "masked_email": mask_email(user.email_address) if user.email_address else None,
    }


@app.post("/api/users/login")
def login(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if not db_user or db_user.password_hash != user.password:
        return {"status": "error", "message": "Invalid username or password"}
    return {"status": "success", "user_id": db_user.id, "username": db_user.username}


# ============================================================
# TRANSACTIONS — Recent history
# ============================================================
@app.get("/api/transactions/recent/{user_id}")
def get_recent_transactions(user_id: int, db: Session = Depends(get_db)):
    return db.query(models.Transaction).filter(
        models.Transaction.user_id == user_id
    ).order_by(models.Transaction.timestamp.desc()).limit(10).all()


#                 cd backend
#                 .\venv\Scripts\Activate
#                 uvicorn main:app --reload