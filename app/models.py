from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from datetime import datetime
from app.database import Base

class User(Base):
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, index=True)
    telegram_name = Column(String, nullable=True)
    first_name = Column(String, nullable=True)

    # 💡 ዋና ማሻሻያ፦ በሚኒ አፑ እና በዳታቤዙ መካከል ያለውን ግጭት ለመፍታት
    balance = Column(Float, default=0.0)    # ለባክኤንድ ስሌቶች የሚጠቅም
    wallet = Column(Float, default=0.0)     # ሚኒ አፑ በቀጥታ 'wallet' ብሎ ስለሚጠራው እዚህም ተጨምሯል
    gift_coin = Column(Float, default=0.0)  # የGift Coin መከታተያ

    is_admin = Column(Boolean, default=False)
    is_banned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Deposit(Base):
    __tablename__ = "deposits"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True) 
    amount = Column(Float)
    
    method = Column(String, nullable=True)        
    phone_or_acc = Column(String, nullable=True) 
    sms_text = Column(Text, nullable=True)         
    tx_hash = Column(String, nullable=True) 
    # 🛠 ማስተካከያ፡ status ወደ 'pending' ተቀይሯል
    status = Column(String, default="pending")    
    approved_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    telegram_id = Column(String, nullable=True)
    wallet = Column(String, nullable=True)
    telegram_name = Column(String, nullable=True)


class Withdrawal(Base):
    __tablename__ = "withdrawals"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    amount = Column(Float)
    
    method = Column(String, nullable=True, default="Bank") 
    wallet = Column(String, nullable=True)        
    # 🛠 ማስተካከያ፡ status ወደ 'pending' ተቀይሯል
    status = Column(String, default="pending") 
    approved_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Card(Base):
    __tablename__ = "cards"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    card_number = Column(Integer, unique=True, index=True) 
    data = Column(Text) 
    is_taken = Column(Boolean, default=False)
    current_game_id = Column(Integer, nullable=True)
    reserved_by = Column(Integer, nullable=True)


class PlayerCard(Base):
    __tablename__ = "player_cards"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, index=True)
    user_id = Column(Integer, index=True)
    card_number = Column(Integer)
    bet_amount = Column(Float, default=0.0)  
    is_winner = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Game(Base):
    __tablename__ = "games"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    status = Column(String, default="waiting") 
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    winner_id = Column(Integer, nullable=True)
    winning_card = Column(Integer, nullable=True)
    prize = Column(Float, default=0.0)
    
    total_players = Column(Integer, default=0)
    total_pool = Column(Float, default=0.0)
    taken_cards = Column(Text, default="[]") 
    drawn_balls = Column(Text, default="[]") 


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    amount = Column(Float)
    transaction_type = Column(String) 
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


class Admin(Base):
    __tablename__ = "admins"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True)
    username = Column(String)
    full_name = Column(String)
    is_super_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    game_id = Column(Integer, ForeignKey("games.id"))
    picked_numbers = Column(Text)
    card_data = Column(Text)
    is_winner = Column(Boolean, default=False)
    prize = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)


class BingoCard(Base):
    __tablename__ = "bingo_cards"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    game_id = Column(Integer, ForeignKey("games.id"))
    card_data = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class AdminStats(Base):
    __tablename__ = "admin_stats"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    house_balance = Column(Float, default=0.0) 
    total_commission = Column(Float, default=0.0)
