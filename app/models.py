from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Date
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class User(Base):
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, index=True)
    telegram_name = Column(String, nullable=True)
    first_name = Column(String, nullable=True)

    # 💡 በሚኒ አፑ እና በዳታቤዙ መካከል ያለውን ግጭት ለመፍታት
    balance = Column(Float, default=0.0)    
    wallet = Column(Float, default=0.0)     
    gift_coin = Column(Float, default=0.0)  
    
    # 🎁 የሪፈራል (የግብዣ ሲስተም) መቆጣጠሪያ ኮለም
    referred_by = Column(String, nullable=True) 

    is_admin = Column(Boolean, default=False)
    is_banned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 🎯 🔴 አዲስ የተጨመሩ፦ ለ Profile፣ Bonus እና Leaderboard የሚሆኑ ቆጣሪዎች
    total_games_played = Column(Integer, default=0)     # በአጠቃላይ የተጫወታቸው ካርዶች ብዛት
    total_games_won = Column(Integer, default=0)        # በአጠቃላይ ያሸነፋቸው ጨዋታዎች ብዛት
    total_winnings = Column(Float, default=0.0)         # በአጠቃላይ ያሸነፈው የብር መጠን

    weekly_games_played = Column(Integer, default=0)    # በሳምንቱ የተጫወታቸው ካርዶች ብዛት
    weekly_deposit_amount = Column(Float, default=0.0)  # በሳምንቱ ያስገባው የብር መጠን


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
    # 📌 String ተደርጓል፤ ምክንያቱም ከአንድ በላይ አሸናፊ ሲኖር "105,106" ተብሎ ሊጻፍ ይችላል
    winning_card = Column(String, nullable=True) 
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
    
    # 📌 አዲስ የተጨመረ፦ የቤት (House) ማሸነፊያ Ratio መቆጣጠሪያ 
    # 3 = (3 House : 1 User), 2 = (2 House : 1 User), 1 = (1 House : 1 User)
    house_win_ratio = Column(Integer, default=3)


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


# 🎁 የዕለታዊ ስጦታ (Daily Check-in) መቆጣጠሪያ ጠረጴዛ
class DailyCheckIn(Base):
    __tablename__ = "daily_checkins"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    checked_date = Column(Date, nullable=False) 
    created_at = Column(DateTime, default=datetime.utcnow)


# 🏆 🔴 አዲስ የተጨመረ፦ የሳምንታዊ ውድድር አሸናፊዎች ታሪክ መመዝገቢያ ጠረጴዛ
class LeaderboardRewardHistory(Base):
    __tablename__ = "leaderboard_rewards"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rank = Column(Integer, nullable=False)             # 1ኛ፣ 2ኛ፣ ወይም 3ኛ
    reward_amount = Column(Float, nullable=False)      # የተሸለመው የብር መጠን
    games_count = Column(Integer, default=0)           # ያሸነፈበት የካርድ/የጨዋታ ብዛት
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
