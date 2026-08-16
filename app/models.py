from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Date
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

# ==========================================
# 👤 1. USER MODEL
# ==========================================
class User(Base):
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, index=True, nullable=False)
    telegram_name = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    phone_number = Column(String, nullable=True, index=True)

    balance = Column(Float, default=0.0)    
    wallet = Column(Float, default=0.0)     
    gift_coin = Column(Float, default=0.0)  

    is_bot = Column(Boolean, default=False)
    referred_by = Column(String, nullable=True, index=True) 

    is_admin = Column(Boolean, default=False)
    is_banned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 🎯 Profile, Bonus & Leaderboard Counters
    total_games_played = Column(Integer, default=0)     
    total_games_won = Column(Integer, default=0)        
    total_winnings = Column(Float, default=0.0)         

    weekly_games_played = Column(Integer, default=0, index=True)    
    weekly_deposit_amount = Column(Float, default=0.0, index=True)  

    # 🔗 Relationships
    deposits = relationship("Deposit", back_populates="user", cascade="all, delete-orphan")
    withdrawals = relationship("Withdrawal", back_populates="user", cascade="all, delete-orphan")
    player_cards = relationship("PlayerCard", back_populates="user", cascade="all, delete-orphan")
    checkins = relationship("DailyCheckIn", back_populates="user", cascade="all, delete-orphan")


# ==========================================
# 💰 2. DEPOSIT MODEL
# ==========================================
class Deposit(Base):
    __tablename__ = "deposits"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True) 
    amount = Column(Float, nullable=False)
    
    method = Column(String, nullable=True)        
    phone_or_acc = Column(String, nullable=True) 
    sms_text = Column(Text, nullable=True)         
    tx_hash = Column(String, nullable=True) 
    status = Column(String, default="pending", index=True)    
    approved_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    telegram_id = Column(String, nullable=True, index=True)
    wallet = Column(String, nullable=True)
    telegram_name = Column(String, nullable=True)

    # 🔗 Relationship
    user = relationship("User", back_populates="deposits")


# ==========================================
# 📤 3. WITHDRAWAL MODEL
# ==========================================
class Withdrawal(Base):
    __tablename__ = "withdrawals"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    amount = Column(Float, nullable=False)
    
    method = Column(String, nullable=True, default="Bank") 
    wallet = Column(String, nullable=True)        
    status = Column(String, default="pending", index=True) 
    approved_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 🔗 Relationship
    user = relationship("User", back_populates="withdrawals")


# ==========================================
# 🎁 4. BONUS & CLAIM MODELS (🔴 አዲስ የተጨመሩ)
# ==========================================
class Bonus(Base):
    __tablename__ = "bonuses"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False)
    amount = Column(Float, nullable=False)
    max_claims = Column(Integer, default=1)
    claimed_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class BonusClaim(Base):
    __tablename__ = "bonus_claims"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    bonus_id = Column(Integer, ForeignKey("bonuses.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    claimed_at = Column(DateTime, default=datetime.utcnow)


# ==========================================
# 🎲 5. GAME & CARD MODELS
# ==========================================
class Card(Base):
    __tablename__ = "cards"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    card_number = Column(Integer, unique=True, index=True) 
    data = Column(Text)  # 5x5 Grid Numbers (JSON format)
    is_taken = Column(Boolean, default=False)
    current_game_id = Column(Integer, nullable=True)
    reserved_by = Column(Integer, nullable=True)


class PlayerCard(Base):
    __tablename__ = "player_cards"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id", ondelete="CASCADE"), index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    card_number = Column(Integer)
    card_data = Column(Text, nullable=True)  
    bet_amount = Column(Float, default=0.0)  
    is_winner = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 🔗 Relationships
    user = relationship("User", back_populates="player_cards")
    game = relationship("Game", back_populates="player_cards")


class Game(Base):
    __tablename__ = "games"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    status = Column(String, default="waiting", index=True) 
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    
    winner_id = Column(Integer, nullable=True) 
    winning_card = Column(String, nullable=True) 
    winners_info = Column(Text, default="[]") 
    
    prize = Column(Float, default=0.0)
    total_players = Column(Integer, default=0)
    total_pool = Column(Float, default=0.0)
    taken_cards = Column(Text, default="[]") 
    drawn_balls = Column(Text, default="[]") 

    # 🔗 Relationship
    player_cards = relationship("PlayerCard", back_populates="game", cascade="all, delete-orphan")


# ==========================================
# 📊 6. TRANSACTIONS & SYSTEM SETTINGS
# ==========================================
class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    amount = Column(Float, nullable=False)
    transaction_type = Column(String, nullable=False) 
    status = Column(String, default="pending")
    telegram_message_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Setting(Base):
    __tablename__ = "settings"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    game_commission_percent = Column(Float, default=20.0) 
    countdown_seconds = Column(Integer, default=30)
    draw_interval = Column(Float, default=2.0)
    max_cards = Column(Integer, default=5)
    min_deposit = Column(Float, default=20.0)
    min_withdraw = Column(Float, default=50.0)
    jackpot_percent = Column(Float, default=10.0)
    is_registration_open = Column(Boolean, default=True)
    house_win_ratio = Column(Integer, default=3)


class Admin(Base):
    __tablename__ = "admins"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, index=True)
    username = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    is_super_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    game_id = Column(Integer, ForeignKey("games.id", ondelete="CASCADE"))
    picked_numbers = Column(Text)
    card_data = Column(Text)
    is_winner = Column(Boolean, default=False)
    prize = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)


class BingoCard(Base):
    __tablename__ = "bingo_cards"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    game_id = Column(Integer, ForeignKey("games.id", ondelete="CASCADE"))
    card_data = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class AdminStats(Base):
    __tablename__ = "admin_stats"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    house_balance = Column(Float, default=0.0) 
    total_commission = Column(Float, default=0.0)


class DailyCheckIn(Base):
    __tablename__ = "daily_checkins"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    checked_date = Column(Date, nullable=False, index=True) 
    created_at = Column(DateTime, default=datetime.utcnow)

    # 🔗 Relationship
    user = relationship("User", back_populates="checkins")


class LeaderboardRewardHistory(Base):
    __tablename__ = "leaderboard_rewards"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    rank = Column(Integer, nullable=False)             
    reward_amount = Column(Float, nullable=False)      
    games_count = Column(Integer, default=0)           
    created_at = Column(DateTime, default=datetime.utcnow)

    # 🔗 Relationship
    user = relationship("User")
