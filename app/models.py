from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from datetime import datetime
from app.database import Base

class User(Base):
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True} # 👈 ድጋሚ መፈጠር እንዳይጋጭ ይከላከላል

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, index=True)
    telegram_name = Column(String)
    first_name = Column(String)

    balance = Column(Float, default=0.0) # የዋናው Wallet ባላንስ
    gift_coin = Column(Float, default=0.0) # አዲሱ የGift Coin መከታተያ ማከማቻ

    is_admin = Column(Boolean, default=False)
    is_banned = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    # 🛠️ ፊክስ፦ ኮፒሎት የሰራው ፍሮንትኤንድ/ባክኤንድ 'wallet' ሲል በቀጥታ 'balance'ን እንዲያገኝ ያደርገዋል
    @property
    def wallet(self):
        return self.balance
    
    @wallet.setter
    def wallet(self, value):
        self.balance = value


class Deposit(Base):
    __tablename__ = "deposits"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Float)
    
    # 💡 በእጅ ማረጋገጫ (Manual Approval) እንዲሰራ የተጨመሩ Column-ዎች
    method = Column(String, nullable=True) 
    phone_or_acc = Column(String, nullable=True) 
    sms_text = Column(Text, nullable=True) 
    
    tx_hash = Column(String, nullable=True) 
    status = Column(String, default="Pending") 
    approved_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 🔗 በ Railway ዳታቤዝህ ላይ በፎቶ ያየናቸውና ግዴታ መካተት ያለባቸው ተጨማሪ አምዶች፡
    telegram_id = Column(String, nullable=True)
    wallet = Column(String, nullable=True)
    telegram_name = Column(String, nullable=True)


class Withdrawal(Base):
    __tablename__ = "withdrawals"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Float)
    
    # 💡 ወደ የትኛው ባንክ/ስልክ እንደሚወጣ ለመለየት የተጨመረ (በዳታቤዝህ ላይ ከሌለ ስህተት እንዳይፈጥር Safe እናድርገው)
    method = Column(String, nullable=True, default="Bank") 
    wallet = Column(String, nullable=True) # አካውንት ቁጥር
    
    status = Column(String, default="Pending") 
    approved_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Card(Base):
    __tablename__ = "cards"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    card_number = Column(Integer, unique=True, index=True) # 1-200 ቁጥር
    data = Column(Text) # የ 5x5 ማትሪክስ ጃሰን ዳታ (JSON String)
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
    bet_amount = Column(Float, default=0.0)  # Store the bet amount for this player card
    is_winner = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Game(Base):
    __tablename__ = "games"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    status = Column(String, default="waiting") # waiting, picking, drawing, finished
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    winner_id = Column(Integer, nullable=True)
    winning_card = Column(Integer, nullable=True)
    prize = Column(Float, default=0.0)
    
    # Track counts and pool
    total_players = Column(Integer, default=0)
    total_pool = Column(Float, default=0.0)

    # 🆕 [አዲሱ ማሻሻያ] በማንኛውም ሰው የተያዙ ካርዶችን ዝርዝር ለሁሉም በዌብሶኬት ለመላክ የሚጠቅም (ጃሰን ዝርዝር ለምን)
    taken_cards = Column(Text, default="[]") 
    drawn_balls = Column(Text, default="[]") # የወደቁ ኳሶችን ዝርዝር በቅደም ተከተል መመዝገቢያ


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    amount = Column(Float)
    transaction_type = Column(String) # deposit, withdraw, bet_place, win_payout
    status = Column(String, default="pending")
    telegram_message_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Setting(Base):
    __tablename__ = "settings"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    # 💡 የጨዋታው ኮሚሽን ፐርሰንት (ባንተ ህግ መሰረት 20% ተደርጓል)
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
    house_balance = Column(Float, default=0.0) # ማንም ያልገዛው ካርድ ሲያሸንፍ ብሩ እዚህ ይከማቻል
    total_commission = Column(Float, default=0.0) # ካሲኖው ከጨዋታዎች የሚቆርጠው ጠቅላላ ኮሚሽን
