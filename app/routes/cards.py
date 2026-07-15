import os
import random
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional

from app.database import SessionLocal
from app.models import User, Game  # 💡 ከባክኤንድህ ሞዴሎች ጋር መናበቡን ያረጋግጣል

router = APIRouter(
    prefix="/api",
    tags=["Bingo Cards"]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --------------------------------------------------------------------------
# 📦 የፒዳንቲክ (Pydantic) ስኪማዎች
# --------------------------------------------------------------------------
# 🎯 ፊክስ፦ ከሚኒ አፑ ከሚላከው 'card_number' ጋር እንዲጣጣም ተደርጓል
class CardSelectionRequest(BaseModel):
    telegram_id: str
    card_number: int      # በሚኒ አፑ የሚላከው የካርድ ቁጥር (1-200)
    bet_amount: float     # የተወራረደበት የብር መጠን

class GameResultRequest(BaseModel):
    telegram_id: str
    game_id: Optional[str] = None
    won: bool
    win_amount: float     # ያሸነፈው የብር መጠን (ካልአሸነፈ 0.0)
    bet_amount: float     # ለመጫወት ያስያዘው የብር መጠን

# --------------------------------------------------------------------------
# 🧮 የቢንጎ ካርቴላ ማመንጫ ሎጂክ (75-Ball Bingo Standard)
# --------------------------------------------------------------------------
def generate_bingo_card(seed_num: Optional[int] = None) -> List[List[int]]:
    """
    ለተጫዋቾች መደበኛ 5x5 የቢንጎ ካርቴላ ያመነጫል።
    B: 1-15, I: 16-30, N: 31-45 (መካከሉ FREE), G: 46-60, O: 61-75
    💡 seed_num ከተሰጠ ለእያንዳንዱ የካርድ ቁጥር ሁልጊዜ አንድ አይነት ካርድ ያመነጫል!
    """
    if seed_num is not None:
        random.seed(seed_num)
        
    ranges = [
        (1, 15),   # B
        (16, 30),  # I
        (31, 45),  # N
        (46, 60),  # G
        (61, 75)   # O
    ]
    
    columns = []
    for start, end in ranges:
        col = random.sample(range(start, end + 1), 5)
        columns.append(col)
    
    # መካከለኛውን አምድ (N) FREE SPACE (0) ማድረግ
    # በሚኒ አፑ ላይ 'FREE' ተብሎ እንዲነበብ በ 0 እንወክለዋለን
    columns[2][2] = 0
    
    # አምዶቹን ወደ ረድፍ (Rows) መቀየር
    card = []
    for i in range(5):
        row = [columns[j][i] for j in range(5)]
        card.append(row)
        
    # የዘፈቀደ ማመንጫውን ለሌላው ክፍል ዳግም ሪሴት ማድረግ
    if seed_num is not None:
        random.seed()
        
    return card

# --------------------------------------------------------------------------
# 🚀 የኤፒአይ (API) ክፍሎች
# --------------------------------------------------------------------------

# 1. 🎴 በሚኒ አፑ ላይ የተገዛውን ካርድ ማትሪክስ (ቁጥሮች) ለማምጣት የሚጠራው ኤፒአይ
@router.get("/cards/get_matrix")
def get_card_matrix(card_number: int):
    """
    ከ 1 እስከ 200 ባለው የካርድ ቁጥር መሠረት ቋሚ ማትሪክስ ያመነጫል
    """
    if card_number < 1 or card_number > 200:
        raise HTTPException(status_code=400, detail="❌ ልክ ያልሆነ የካርድ ቁጥር!")
        
    matrix = generate_bingo_card(seed_num=card_number)
    
    # 0 የነበረውን ወደ "FREE" መለወጥ (ከሚኒ አፑ ጋር እንዲገጥም)
    formatted_matrix = []
    for row in matrix:
        formatted_row = []
        for val in row:
            formatted_row.append("FREE" if val == 0 else val)
        formatted_matrix.append(formatted_row)
        
    return {"success": True, "card_number": card_number, "matrix": formatted_matrix}


# 2. 💸 ተጫዋቹ ካርቴላ ሲገዛ (Confirm Pick / Deduct Balance)
# 🎯 ፊክስ፦ አድራሻው በሚኒ አፑ ወደሚጠራው '/cards/pick' ተቀይሯል
@router.post("/cards/pick")
def select_card_and_bet(req: CardSelectionRequest, db: Session = Depends(get_db)):
    tg_id_str = str(req.telegram_id).strip()
    
    # ተጠቃሚውን ከዳታቤዝ መፈለግ
    user = db.query(User).filter(User.telegram_id == tg_id_str).first()
    if not user:
        return {
            "success": False,
            "message": "❌ ተጠቃሚው አልተመዘገበም! እባክዎ መጀመሪያ ሚኒ አፑን ይክፈቱ።"
        }
    
    # የሳንቲም/የብር መጠን መፈተሽ
    user_balance = getattr(user, "balance", 0.0) or 0.0
    if user_balance < req.bet_amount:
        return {
            "success": False, 
            "message": f"ይቅርታ፣ ለመጫወት በቂ ባላንስ የሎትም! ያሎት ቀሪ ሂሳብ {user_balance} ETB ነው።",
            "current_balance": user_balance
        }
    
    # 📉 እውነተኛውን ባላንስ መቀነስ
    try:
        user.balance = user_balance - req.bet_amount
        # wallet ካለህ እሱንም አብረህ አስተካክለው
        if hasattr(user, "wallet"):
            user.wallet = user.balance
            
        db.commit()
        db.refresh(user)
    except Exception as e:
        db.rollback()
        return {"success": False, "message": f"የዳታቤዝ ስህተት አጋጥሟል፦ {str(e)}"}
    
    return {
        "success": True,
        "message": f"🎰 ካርድ #{req.card_number} በተሳካ ሁኔታ ተገዝቷል!",
        "card_number": req.card_number,
        "current_balance": user.balance
    }


# 3. 🏆 የጨዋታው ውጤት ሲታወቅ (Win / Lose handler)
@router.post("/cards/result")
def process_game_result(req: GameResultRequest, db: Session = Depends(get_db)):
    tg_id_str = str(req.telegram_id).strip()
    
    user = db.query(User).filter(User.telegram_id == tg_id_str).first()
    if not user:
        raise HTTPException(status_code=404, detail="ተጠቃሚው አልተገኘም")
    
    current_balance = getattr(user, "balance", 0.0) or 0.0
    
    # 💰 ተጫዋቹ ካሸነፈ ያሸነፈውን ብር በትክክል መደመር
    if req.won and req.win_amount > 0:
        new_balance = current_balance + req.win_amount
        user.balance = new_balance
        if hasattr(user, "wallet"):
            user.wallet = new_balance
        message_detail = f"🎉 እንኳን ደስ የአሎት! {req.win_amount} ETB አሸንፈው ወደ አካውንቶ ተጨምሯል።"
    else:
        new_balance = current_balance
        message_detail = "😢 በዚህ ዙር አልተሳካም፣ መልካም እድል ለቀጣይ ዙር!"
        
    try:
        # የጨዋታ ታሪክ መዝገብ ማስቀመጥ
        new_game_record = Game(
            user_id=user.id,
            bet_amount=req.bet_amount,
            win_amount=req.win_amount if req.won else 0.0,
            status="won" if req.won else "lost",
            created_at=datetime.utcnow()
        )
        db.add(new_game_record)
        db.commit()
        db.refresh(user)
    except Exception as e:
        db.rollback()
        print(f"⚠️ የጨዋታ መዝገብ ማስቀመጥ አልተቻለም (ግን ባላንሱ ተስተካክሏል)፦ {e}")
        db.commit() # የተጫዋቹን ባላንስ ለማዳን
        
    return {
        "success": True,
        "message": message_detail,
        "won": req.won,
        "updated_balance": user.balance
    }
