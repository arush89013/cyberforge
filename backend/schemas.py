from pydantic import BaseModel
class UserCreate(BaseModel):
    username: str
    password: str

class TransactionCreate(BaseModel):
    user_id: int
    amount: float
    recipient: str
    device_info: str
    location_ip: str

class HardwareVerify(BaseModel):
    transaction_id: int
    hardware_id: str
    status: str