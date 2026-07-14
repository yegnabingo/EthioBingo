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
class CardSelectionRequest(BaseModel):
    telegram_id: str
    card_index: int       # የካርቴላው ቁጥር (0, 1, 2, 3...)
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
def generate_bingo_card() -> List[List[int]]:
    """
    ለተጫዋቾች መደበኛ 5x5 የቢንጎ ካርቴላ ያመነጫል።
    B: 1-15, I: 16-30, N: 31-45 (መካከሉ 0/FREE), G: 46-60, O: 61-75
    """
    card = []
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
    columns[2][2] = 0
    
    # አምዶቹን ወደ ረድፍ (Rows) መቀየር
    for i in range(5):
        row = [columns[j][i] for j in range(5)]
        card.append(row)
        
    return card

# --------------------------------------------------------------------------
# 🚀 የኤፒአይ (API) ክፍሎች
# --------------------------------------------------------------------------

# 1. 🎴 ተጫዋቹ የሚመርጣቸውን የካርቴላ አማራጮች ማመንጫ
@router.get("/cards/generate-options")
def get_card_options(count: int = 6):
    """
    ተጫዋቹ ሚኒ አፑን ሲከፍት የሚመርጣቸውን ስድስት (ወይም የተፈለገውን ያህል) 
    የተለያዩ የካርቴላ አማራጮች ያመነጫል።
    """
    options = []
    for i in range(count):
        options.append({
            "card_index": i,
            "matrix": generate_bingo_card()
        })
    return {"success": True, "cards": options}


# 2. 💸 ተጫዋቹ ካርቴላ መርጦ ውርርድ ሲያስይዝ (Bet / Deduct Balance)
@router.post("/cards/select")
def select_card_and_bet(req: CardSelectionRequest, db: Session = Depends(get_db)):
    tg_id_str = str(req.telegram_id).strip()
    
    # ተጠቃሚውን ከዳታቤዝ መፈለግ
    user = db.query(User).filter(User.telegram_id == tg_id_str).first()
    if not user:
        raise HTTPException(
            status_code=404, 
            detail="❌ ተጠቃሚው አልተመዘገበም! እባክዎ መጀመሪያ በቴሌግራም ቦቱ በኩል ይግቡ።"
        )
    
    # የሳንቲም/የብር መጠን መፈተሽ
    user_balance = getattr(user, "balance", 0.0) or 0.0
    if user_balance < req.bet_amount:
        return {
            "success": False, 
            "message": f"❌ ይቅርታ፣ ለመጫወት በቂ ባላንስ የሎትም! ያሎት ቀሪ ሂሳብ {user_balance} ETB ነው።",
            "current_balance": user_balance
        }
    
    # 📉 እውነተኛውን ባላንስ መቀነስ (ከውሸት 500 ብር ነፃ ስጦታ የጸዳ)
    try:
        user.balance = user_balance - req.bet_amount
        user.wallet = user.balance  # ሁለቱንም ተናባቢ ማድረግ
        db.commit()
        db.refresh(user)
    except Exception as e:
        db.rollback()
        return {"success": False, "message": f"የዳታቤዝ ስህተት አጋጥሟል፦ {str(e)}"}
    
    return {
        "success": True,
        "message": f"🎰 ውርርድ በተሳካ ሁኔታ ተይዟል! {req.bet_amount} ETB ተቀንሷል።",
        "card_index": req.card_index,
        "remaining_balance": user.balance
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
        user.wallet = new_balance
        message_detail = f"🎉 እንኳን ደስ የአሎት! {req.win_amount} ETB አሸንፈው ወደ አካውንቶ ተጨምሯል።"
    else:
        # ከተሸነፈ አስቀድሞ በ `/cards/select` ላይ ስለተቀነሰ እዚህ ተጨማሪ ብር አንቀንስም
        new_balance = current_balance
        message_detail = "😢 በዚህ ዙር አልተሳካም፣ መልካም እድል ለቀጣይ ዙር!"
        
    try:
        # የጨዋታ ታሪክ መዝገብ (Game History) ካለህ ለማስቀመጥ
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
