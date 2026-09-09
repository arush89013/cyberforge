from fastapi import FastAPI, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import SessionLocal, engine, Base
import models
import schemas
from datetime import datetime, timezone

from ai_engine.predictor import evaluate_risk

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


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================
# HELPER: Compute user behavioral baselines from history
# ============================================================
def compute_user_baselines(db: Session, user_id: int) -> dict:
    """
    Query the user's past completed transactions to build a
    behavioral baseline for the AI engine.
    """
    completed_statuses = ["Completed", "OTP_Awaiting", "ESP32_Awaiting"]

    past_transactions = db.query(models.Transaction).filter(
        models.Transaction.user_id == user_id,
        models.Transaction.status.in_(completed_statuses)
    ).all()

    if not past_transactions:
        return {"avg_amount": None, "avg_typing_speed": None}

    # Average transaction amount
    amounts = [tx.amount for tx in past_transactions if tx.amount is not None]
    avg_amount = sum(amounts) / len(amounts) if amounts else None

    # Average typing speed (only from transactions that recorded it)
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
    # ----------------------------------------------------------
    # 1. AUTO-DETECT CLIENT IP (server-side, not from payload)
    # ----------------------------------------------------------
    client_ip = request.client.host if request.client else "unknown"

    # ----------------------------------------------------------
    # 2. DEVICE & LOCATION PROFILING (from history)
    # ----------------------------------------------------------
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

    # ----------------------------------------------------------
    # 3. COMPUTE USER BEHAVIORAL BASELINES
    # ----------------------------------------------------------
    baselines = compute_user_baselines(db, tx.user_id)

    # ----------------------------------------------------------
    # 4. BUILD 5-DIMENSIONAL FEATURE VECTOR FOR AI ENGINE
    # ----------------------------------------------------------
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

    # ----------------------------------------------------------
    # 5. AI RISK EVALUATION
    # ----------------------------------------------------------
    ai_result = evaluate_risk(transaction_data)
    actual_risk_score = ai_result["risk_score"]

    # ----------------------------------------------------------
    # 6. UPGRADED DECISION ENGINE
    # ----------------------------------------------------------
    #   < 25  → PIN only (trusted)
    #  25–59  → OTP required (some anomaly)
    #  60–79  → OTP + strong warning (multiple anomalies)
    #   >= 80 → Hardware auth (ESP32 required)
    # ----------------------------------------------------------

    if actual_risk_score < 25:
        # Low risk — PIN-based authentication
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

    elif actual_risk_score < 60:
        final_status = "OTP_Awaiting"
        action = "REQUIRE_OTP"

    elif actual_risk_score < 80:
        final_status = "OTP_Awaiting"
        action = "REQUIRE_OTP"
        # Stronger warning flags are already in ai_result["flags"]

    else:
        final_status = "ESP32_Awaiting"
        action = "REQUIRE_HARDWARE_AUTH"

    # ----------------------------------------------------------
    # 7. SAVE TO DATABASE (with new fields)
    # ----------------------------------------------------------
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

    return {
        "transaction_id": new_tx.id,
        "risk_score": actual_risk_score,
        "action": action,
        "flags": ai_result["flags"],
        "sub_scores": ai_result["sub_scores"],
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

    if verification.status == "APPROVED":
        tx.status = "Completed"
    else:
        tx.status = "Blocked"

    db.commit()
    return {"message": f"Transaction {tx.id} updated to {tx.status}"}


# ============================================================
# USER — Registration, login, PIN management
# ============================================================
@app.post("/api/users/register")
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    new_user = models.User(
        username=user.username,
        password_hash=user.password
    )
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
    transactions = db.query(models.Transaction).filter(
        models.Transaction.user_id == user_id
    ).order_by(models.Transaction.timestamp.desc()).limit(10).all()

    return transactions


# venv\Scripts\activate
# uvicorn main:app --reload