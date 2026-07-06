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
    telegram_name: str
    first_name: str
    balance: float
    gift_coin: float # 🆕 በUI ላይ Wallet እና Gift Coin ለማሳየት የተጨመረ

    class Config:
        from_attributes = True


# -------------------------
# 🎴 Card Pick Schemas (ከ app.js ሎጂክ ጋር የተጣጣመ)
# -------------------------
class PickCardRequest(BaseModel):
    telegram_id: str
    card_number: int
    bet_amount: float # 🆕 በጃቫስክሪፕቱ ፌች (fetch) ጥሪ ላይ የላክነውን ውርርድ መጠን ለመቀበል


class PickCardResponse(BaseModel):
    success: bool
    message: str
    current_balance: Optional[float] = None # 🆕 ግዢው ሲሳካ የቲጂ ሚኒ አፑ ባላንስን በቅጽበት እንዲያድስ


# -------------------------
# 💵 Deposit Schemas (ለበእጅ ማረጋገጫ የዘመነ)
# -------------------------
class DepositCreate(BaseModel):
    amount: float
    method: str # Telebirr, CBE, ወዘተ
    phone_or_acc: Optional[str] = None # የላከበት ስልክ ቁጥር ወይም አካውንት
    sms_text: Optional[str] = None # ተጠቃሚው የለጠፈው የግብይት ማረጋገጫ SMS
    tx_hash: Optional[str] = None


class DepositResponse(BaseModel):
    id: int
    user_id: int
    amount: float
    method: Optional[str]
    status: str # Pending, Approved, Rejected
    created_at: datetime

    class Config:
        from_attributes = True


# -------------------------
# 💸 Withdraw Schemas (ለባንክ እና ቴሌብር መውጫ የዘመነ)
# -------------------------
class WithdrawCreate(BaseModel):
    amount: float
    method: str # Telebirr, CBE, ወዘተ
    wallet: str # ብሩ የሚላክበት የባንክ አካውንት ወይም ስልክ ቁጥር


class WithdrawResponse(BaseModel):
    id: int
    user_id: int
    amount: float
    method: Optional[str]
    wallet: str
    status: str # Pending, Approved, Rejected
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
    taken_cards: str # የ 1-200 ቁልፎችን ቀለም ለመቀየር ወደ ፊት ገጽ የሚላክ ጃሰን ዝርዝር
    
    class Config:
        from_attributes = True
