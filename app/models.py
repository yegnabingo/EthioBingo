from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from datetime import datetime

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    telegram_id = Column(String, unique=True, index=True)
    telegram_name = Column(String)
    first_name = Column(String)

    balance = Column(Float, default=0)

    is_admin = Column(Boolean, default=False)
    is_banned = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)


class Deposit(Base):
    __tablename__ = "deposits"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Float)
    
    # 💡 በእጅ ማረጋገጫ (Manual Approval) እንዲሰራ የተጨመሩ Column-ዎች
    method = Column(String, nullable=True) # Telebirr, CBE, Bank ወዘተ
    phone_or_acc = Column(String, nullable=True) # የላከበት ስልክ
    sms_text = Column(Text, nullable=True) # ተጠቃሚው የለጠፈው SMS
    
    tx_hash = Column(String, nullable=True) # የነበረው (እንዳይጠፋ)
    status = Column(String, default="Pending") # Pending, Approved, Rejected
    approved_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)



class Withdrawal(Base):
    __tablename__ = "withdrawals"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Float)
    
    # 💡 ወደ የትኛው ባንክ/ስልክ እንደሚወጣ ለመለየት የተጨመረ
    method = Column(String, nullable=True) # Telebirr, CBE, ወዘተ
    wallet = Column(String) # የባንክ ወይም የቴሌብር አካውንት ቁጥር
    
    status = Column(String, default="Pending") # Pending, Approved, Rejected
    approved_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Card(Base):
    __tablename__ = "cards"

    id = Column(Integer, primary_key=True, index=True)

    card_number = Column(Integer, unique=True, index=True)

    data = Column(Text)

    is_taken = Column(Boolean, default=False)

    current_game_id = Column(Integer, nullable=True)

    reserved_by = Column(Integer, nullable=True)


class PlayerCard(Base):
    __tablename__ = "player_cards"

    id = Column(Integer, primary_key=True, index=True)

    game_id = Column(Integer, index=True)

    user_id = Column(Integer, index=True)

    card_number = Column(Integer)

    is_winner = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)


class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True, index=True)

    status = Column(String, default="waiting")

    started_at = Column(DateTime, nullable=True)

    finished_at = Column(DateTime, nullable=True)

    winner_id = Column(Integer, nullable=True)

    winning_card = Column(Integer, nullable=True)

    prize = Column(Float, default=0)


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, index=True)

    amount = Column(Float)

    transaction_type = Column(String)

    status = Column(String, default="pending")

    telegram_message_id = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


class Setting(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)

    # 💡 የጨዋታው ኮሚሽን ፐርሰንት (በአንተ ህግ መሰረት 20% ተደርጓል)
    game_commission_percent = Column(Float, default=20.0) 

    countdown_seconds = Column(Integer, default=30)
    draw_interval = Column(Float, default=2.0)
    max_cards = Column(Integer, default=5)
    min_deposit = Column(Float, default=20)
    min_withdraw = Column(Float, default=50)
    jackpot_percent = Column(Float, default=10)
    is_registration_open = Column(Boolean, default=True)


class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True)

    telegram_id = Column(String, unique=True)

    username = Column(String)

    full_name = Column(String)

    is_super_admin = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id"))

    game_id = Column(Integer, ForeignKey("games.id"))

    picked_numbers = Column(Text)

    card_data = Column(Text)

    is_winner = Column(Boolean, default=False)

    prize = Column(Float, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)


class BingoCard(Base):
    __tablename__ = "bingo_cards"

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id"))

    game_id = Column(Integer, ForeignKey("games.id"))

    card_data = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)


class AdminStats(Base):
    __tablename__ = "admin_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    house_balance = Column(Float, default=0.0) # ማንም ያልገዛው ካርድ ሲያሸንፍ ብሩ እዚህ ይከማቻል
    total_commission = Column(Float, default=0.0) # ካሲኖው ከጨዋታዎች የሚቆርጠው ጠቅላላ ኮሚሽን
