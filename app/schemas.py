from pydantic import BaseModel
from typing import List


# -------------------------
# User
# -------------------------

class UserCreate(BaseModel):
    telegram_id: str
    telegram_name: str
    first_name: str


class UserResponse(BaseModel):
    id: int
    telegram_id: str
    telegram_name: str
    first_name: str
    balance: float

    class Config:
        from_attributes = True


# -------------------------
# Card Pick
# -------------------------

class PickCardRequest(BaseModel):
    telegram_id: str
    card_number: int


class PickCardResponse(BaseModel):
    success: bool
    message: str


# -------------------------
# Deposit
# -------------------------

class DepositCreate(BaseModel):
    amount: float
    tx_hash: str


# -------------------------
# Withdraw
# -------------------------

class WithdrawCreate(BaseModel):
    amount: float
    wallet: str


# -------------------------
# Ticket
# -------------------------

class TicketCreate(BaseModel):
    numbers: List[int]
