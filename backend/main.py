from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
import models
import schemas
import random

from ai_engine.predictor import evaluate_risk

# Automatically create tables in MySQL
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Banking Sentinel API")
from fastapi.middleware.cors import CORSMiddleware

# This allows Neeraj's HTML file to talk to your server
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


# Inside main.py (Scroll down to the transfer route)
@app.post("/api/transactions/transfer")
def initiate_transfer(tx: schemas.TransactionCreate, db: Session = Depends(get_db)):
    # 1. DYNAMIC PROFILING: Has this user succeeded from this IP/Device before?
    known_ip = db.query(models.Transaction).filter(
        models.Transaction.user_id == tx.user_id,
        models.Transaction.location_ip == tx.location_ip,
        models.Transaction.status == "Completed"
    ).first() is not None

    known_device = db.query(models.Transaction).filter(
        models.Transaction.user_id == tx.user_id,
        models.Transaction.device_info == tx.device_info,
        models.Transaction.status == "Completed"
    ).first() is not None

    # 2. ASK THE HARDER AI
    transaction_data = {
        "amount": tx.amount,
        "is_known_ip": known_ip,
        "is_known_device": known_device
    }
    ai_result = evaluate_risk(transaction_data)
    actual_risk_score = ai_result["risk_score"]

    # 3. DECISION ENGINE
    if actual_risk_score < 30:
        final_status = "Completed"
        action = "ALLOW"
    elif actual_risk_score < 75:
        final_status = "OTP_Awaiting"
        action = "REQUIRE_OTP"
    else:
        final_status = "ESP32_Awaiting"
        action = "REQUIRE_HARDWARE_AUTH"

    # 4. SAVE TO DATABASE (Now includes device and IP)
    new_tx = models.Transaction(
        user_id=tx.user_id,
        amount=tx.amount,
        recipient_account=tx.recipient,
        status=final_status,
        device_info=tx.device_info,
        location_ip=tx.location_ip
    )
    db.add(new_tx)
    db.commit()
    db.refresh(new_tx)

    return {
        "transaction_id": new_tx.id,
        "risk_score": actual_risk_score,
        "action": action,
        "flags": ai_result["flags"]
    }

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


@app.post("/api/users/register")
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # Create a new user without forcing the ID!
    # MySQL will auto-increment it automatically.
    new_user = models.User(
        username=user.username,
        password_hash=user.password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)  # This grabs the newly generated ID from MySQL

    return {"message": f"User {new_user.id} created successfully!"}

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


@app.post("/api/users/login")
def login(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()

    if not db_user or db_user.password_hash != user.password:
        return {"status": "error", "message": "Invalid username or password"}

    return {"status": "success", "user_id": db_user.id, "username": db_user.username}


@app.get("/api/transactions/recent/{user_id}")
def get_recent_transactions(user_id: int, db: Session = Depends(get_db)):
    # Fetch the 10 most recent transactions for this user
    transactions = db.query(models.Transaction).filter(
        models.Transaction.user_id == user_id
    ).order_by(models.Transaction.timestamp.desc()).limit(10).all()

    return transactions


#venv\Scripts\activate
#uvicorn main:app --reload