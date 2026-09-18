from pydantic import BaseModel
from typing import Optional


class UserCreate(BaseModel):
    username: str
    password: str


class PinUpdate(BaseModel):
    pin: str


class EmailUpdate(BaseModel):
    email: str


class TransactionCreate(BaseModel):
    user_id: int
    amount: float
    recipient: str
    device_info: Optional[str] = "unknown"
    typing_speed_ms: Optional[float] = None
    pin: Optional[str] = None


class HardwareVerify(BaseModel):
    transaction_id: int
    hardware_id: str
    status: str


class OTPVerify(BaseModel):
    transaction_id: int
    otp: str