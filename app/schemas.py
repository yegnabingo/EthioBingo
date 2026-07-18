from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


# -------------------------
# 👤 User Schemas
# -------------------------

class UserCreate(BaseModel):
    telegram_id: str
    telegram_name: str
    first_name: str


class UserResponse(BaseModel):
    id: int
    telegram_id: str
    telegram_name: Optional[str] = None
    first_name: Optional[str] = None

    balance: float
    wallet: float
    gift_coin: float

    class Config:
        from_attributes = True



# -------------------------
# 🎴 Card Pick Schemas
# -------------------------

class PickCardRequest(BaseModel):
    telegram_id: str
    card_number: int
    bet_amount: float


class PickCardResponse(BaseModel):
    success: bool
    message: str
    current_balance: Optional[float] = None



# -------------------------
# 💵 Deposit Schemas
# -------------------------

class DepositCreate(BaseModel):
    telegram_id: str
    telegram_name: Optional[str] = "ተጫዋች"

    amount: float

    # ከ models.py Deposit.method ጋር
    method: str

    # ከ models.py Deposit.sms_text ጋር
    sms_text: str



class DepositResponse(BaseModel):
    id: int
    user_id: Optional[int] = None

    amount: float

    tx_hash: Optional[str] = None

    # pending / approved / rejected
    status: str

    created_at: datetime


    class Config:
        from_attributes = True



# -------------------------
# 💸 Withdraw Schemas
# -------------------------

class WithdrawCreate(BaseModel):
    telegram_id: str

    amount: float

    # ከ Withdrawal.method ጋር
    method: str

    # ከ Withdrawal.wallet ጋር
    wallet: str



class WithdrawResponse(BaseModel):
    id: int
    user_id: Optional[int] = None

    amount: float

    wallet: str

    # pending / approved / rejected
    status: str

    created_at: datetime


    class Config:
        from_attributes = True



# -------------------------
# 🎫 Ticket & Game Schemas
# -------------------------

class TicketCreate(BaseModel):
    numbers: List[int]



class GameResponse(BaseModel):
    id: int
    status: str
    prize: float
    taken_cards: str

    class Config:
        from_attributes = True
