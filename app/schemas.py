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
# 💵 Deposit Schemas (ከ app.js payload ጋር ፍጹም የተጣጣመ 🛠)
# -------------------------
class DepositCreate(BaseModel):
    telegram_id: str      # 👈 ከጃቫስክሪፕቱ payload በቀጥታ ለማንበብ የተጨመረ
    telegram_name: Optional[str] = "ተጫዋች"
    amount: float
    bank_name: str        # 👈 'method' የነበረው በጃቫስክሪፕቱ 'bank_name' ተተክቷል
    sms_data: str         # 👈 'sms_text' የነበረው በጃቫስክሪፕቱ 'sms_data' ተተክቷል


class DepositResponse(BaseModel):
    id: int
    user_id: int
    amount: float
    tx_hash: Optional[str]  # 👈 በዳታቤዝህ ላይ ካለው እውነተኛ ኮለም ጋር እንዲገጥም ተስተካከለ
    status: str             # Pending, Approved, Rejected
    created_at: datetime

    class Config:
        from_attributes = True


# -------------------------
# 💸 Withdraw Schemas (ከ app.js payload ጋር ፍጹም የተጣጣመ 🛠)
# -------------------------
class WithdrawCreate(BaseModel):
    telegram_id: str      # 👈 ከጃቫስክሪፕቱ payload በቀጥታ ለማንበብ የተጨመረ
    amount: float
    bank_name: str        # 👈 'method' የነበረው በጃቫስክሪፕቱ 'bank_name' ተተክቷል
    account_number: str   # 👈 'wallet' የነበረው በጃቫስክሪፕቱ 'account_number' ተተክቷል


class WithdrawResponse(BaseModel):
    id: int
    user_id: int
    amount: float
    wallet: str           # 👈 በዳታቤዝህ ላይ ካለው እውነተኛ ኮለም ጋር እንዲገጥም ተስተካከለ
    status: str           # Pending, Approved, Rejected
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
