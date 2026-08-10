from pydantic import BaseModel
from typing import List, Optional, Any
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
# 📜 Transaction History Schema
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
# 👤 Profile Full Response Schema
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
# 🏆 Leaderboard / Rank Schema
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
# 🎯 🆕 Winner & Game History Schemas (ለ History Modal የተጨመሩ)
# -------------------------
class WinnerDetailSchema(BaseModel):
    winner_name: str
    phone_number: Optional[str] = "ስልክ አልተመዘገበም"
    winning_card_number: Any
    prize: float
    card_numbers: List[Any] = []     # የ 5x5 Grid 25 ቁጥሮች
    winning_numbers: List[int] = []  # ያሸነፈበት መስመር የተጠሩ ቁጥሮች


class GameHistoryItem(BaseModel):
    game_id: int
    game_no: int
    user_picked_cards: List[int] = []
    winners: List[WinnerDetailSchema] = []
    drawn_balls: List[int] = []
    finished_at: Optional[str] = None


class GameHistoryResponse(BaseModel):
    success: bool
    history: List[GameHistoryItem] = []


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
