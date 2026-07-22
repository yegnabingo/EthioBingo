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
    wallet: float
    gift_coin: float
    total_games_played: Optional[int] = 0
    total_games_won: Optional[int] = 0
    total_winnings: Optional[float] = 0.0
    weekly_games_played: Optional[int] = 0

    class Config:
        from_attributes = True


# -------------------------
# 📜 Transaction History Schema (🆕 ለ Profile Modal የተጨመረ)
# -------------------------
class TransactionHistoryItem(BaseModel):
    id: int
    amount: float
    type: str         # deposit / withdraw
    status: str       # pending / completed / rejected
    created_at: str

    class Config:
        from_attributes = True


# -------------------------
# 👤 Profile Full Response Schema (🆕 ለ UI Profile Modal)
# -------------------------
class UserProfileResponse(BaseModel):
    id: int
    telegram_id: str
    telegram_name: str
    balance: float
    gift_coin: float
    total_games_played: int
    total_games_won: int
    total_winnings: float
    weekly_games_played: int
    transactions: List[TransactionHistoryItem] = []

    class Config:
        from_attributes = True


# -------------------------
# 🏆 Leaderboard / Rank Schema (🆕 ለ UI Rank Modal)
# -------------------------
class LeaderboardUserResponse(BaseModel):
    rank: Optional[int] = None
    telegram_id: str
    telegram_name: str
    weekly_games_played: int
    total_winnings: float

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
    bank_name: str
    sms_data: str


class DepositResponse(BaseModel):
    id: int
    user_id: int
    amount: float
    tx_hash: Optional[str] = None
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
    bank_name: str
    account_number: str


class WithdrawResponse(BaseModel):
    id: int
    user_id: int
    amount: float
    wallet: str
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
