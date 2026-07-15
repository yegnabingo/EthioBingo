import os
import random
import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional

from app.database import SessionLocal
from app.models import User, Game, PlayerCard, Card  # 💡 ካሉህ ሞዴሎች ጋር እንዲስማማ ተደርጓል

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
    card_number: int      # በሚኒ አፑ የሚላከው የካርድ ቁጥር (1-200)
    bet_amount: float     # የተወራረደበት የብር መጠን

class GameResultRequest(BaseModel):
    telegram_id: str
    game_id: Optional[str] = None
    won: bool
    win_amount: float     # ያሸነፈው የብር መጠን (ካልአሸነፈ 0.0)
    bet_amount: float     # ለመጫወት ያስያዘው የብር መጠን

# --------------------------------------------------------------------------
# 🧮 የቢንጎ ካርቴላ ማመንጫ ሎጂክ
# --------------------------------------------------------------------------
def generate_bingo_card(seed_num: Optional[int] = None) -> List[List[int]]:
    if seed_num is not None:
        random.seed(seed_num)
        
    ranges = [(1, 15), (16, 30), (31, 45), (46, 60), (61, 75)]
    columns = []
    for start, end in ranges:
        col = random.sample(range(start, end + 1), 5)
        columns.append(col)
    
    columns[2][2] = 0  # መካከለኛው FREE SPACE
    
    card = []
    for i in range(5):
        row = [columns[j][i] for j in range(5)]
        card.append(row)
        
    if seed_num is not None:
        random.seed()
        
    return card

# --------------------------------------------------------------------------
# 🚀 የኤፒአይ (API) ክፍሎች
# --------------------------------------------------------------------------

# 1. 🎴 የተገዛውን ካርድ ማትሪክስ (ቁጥሮች) ለማምጣት
@router.get("/cards/get_matrix")
def get_card_matrix(card_number: int):
    if card_number < 1 or card_number > 200:
        raise HTTPException(status_code=400, detail="❌ ልክ ያልሆነ የካርድ ቁጥር!")
        
    matrix = generate_bingo_card(seed_num=card_number)
    
    formatted_matrix = []
    for row in matrix:
        formatted_row = []
        for val in row:
            formatted_row.append("FREE" if val == 0 else val)
        formatted_matrix.append(formatted_row)
        
    return {"success": True, "card_number": card_number, "matrix": formatted_matrix}


# 2. 💸 ተጫዋቹ ካርቴላ ሲገዛ (Confirm Pick እና በዳታቤዝ መመዝገቢያ)
@router.post("/cards/pick")
def select_card_and_bet(req: CardSelectionRequest, db: Session = Depends(get_db)):
    tg_id_str = str(req.telegram_id).strip()
    
    # 1️⃣ ተጠቃሚውን መፈለግ
    user = db.query(User).filter(User.telegram_id == tg_id_str).first()
    if not user:
        return {
            "success": False,
            "message": "❌ ተጠቃሚው አልተመዘገበም! እባክዎ መጀመሪያ ሚኒ አፑን ይክፈቱ።"
        }
    
    # 2️⃣ በአሁኑ ሰዓት ያለውን ንቁ ጨዋታ (Active Game) መፈለግ
    # 'waiting' ወይም 'PICK' ስታተስ ላይ ያለውን ጨዋታ እንወስዳለን
    active_game = db.query(Game).filter(Game.status.in_(["waiting", "PICK", "pick"])).first()
    if not active_game:
        # ንቁ ጨዋታ ከሌለ አዲስ እንፈጥራለን
        active_game = Game(status="waiting", total_players=0, total_pool=0.0)
        db.add(active_game)
        db.commit()
        db.refresh(active_game)
    
    # 3️⃣ ካርዱ ቀድሞ መወሰዱን መፈተሽ
    existing_purchase = db.query(PlayerCard).filter(
        PlayerCard.game_id == active_game.id,
        PlayerCard.card_number == req.card_number
    ).first()
    
    if existing_purchase:
        return {
            "success": False,
            "message": f"⚠️ ይቅርታ፣ ካርድ #{req.card_number} ቀደም ብሎ በሌላ ተጫዋች ተገዝቷል!"
        }
        
    # 4️⃣ ባላንስ መፈተሽ
    user_balance = getattr(user, "balance", 0.0) or 0.0
    if user_balance < req.bet_amount:
        return {
            "success": False, 
            "message": f"ይቅርታ፣ ለመጫወት በቂ ባላንስ የሎትም! ያሎት ቀሪ ሂሳብ {user_balance} ETB ነው።",
            "current_balance": user_balance
        }
    
    # 5️⃣ ባላንስ መቀነስ እና ግዢውን መመዝገብ
    try:
        # ሀ. ባላንስ መቀነስ
        user.balance = user_balance - req.bet_amount
        if hasattr(user, "wallet"):
            user.wallet = user.balance
            
        # ለ. የካርድ ግዢውን በ 'player_cards' ሰንጠረዥ ላይ መመዝገብ (የሞተሩ ዋነኛ ምንጭ)
        new_player_card = PlayerCard(
            game_id=active_game.id,
            user_id=user.id,
            card_number=req.card_number,
            bet_amount=req.bet_amount,
            is_winner=False
        )
        db.add(new_player_card)
        
        # ሐ. በ 'cards' ሰንጠረዥ ላይ ካርዱ መወሰዱን መመዝገብ
        db_card = db.query(Card).filter(Card.card_number == req.card_number).first()
        if db_card:
            db_card.is_taken = True
            db_card.current_game_id = active_game.id
            db_card.reserved_by = user.id
        else:
            # ካርዱ በሰንጠረዡ ውስጥ ከሌለ አዲስ ፈጥረን እንመዘግበዋለን
            new_card_entry = Card(
                card_number=req.card_number,
                data=json.dumps(generate_bingo_card(seed_num=req.card_number)),
                is_taken=True,
                current_game_id=active_game.id,
                reserved_by=user.id
            )
            db.add(new_card_entry)
            
        # መ. የጨዋታውን ጠቅላላ ተጫዋች እና የገንዘብ መጠን (pool) ማሳደግ
        active_game.total_players += 1
        active_game.total_pool += req.bet_amount
        
        # የወሰዱትን የካርዶች ዝርዝር በጌሙ ላይ ማደስ (JSON array string)
        try:
            taken_list = json.loads(active_game.taken_cards or "[]")
        except:
            taken_list = []
        if req.card_number not in taken_list:
            taken_list.append(req.card_number)
        active_game.taken_cards = json.dumps(taken_list)

        db.commit()
        db.refresh(user)
    except Exception as e:
        db.rollback()
        print(f"❌ DATABASE ERROR: {str(e)}")
        return {"success": False, "message": f"የዳታቤዝ ስህተት አጋጥሟል፦ {str(e)}"}
    
    return {
        "success": True,
        "message": f"🎰 ካርድ #{req.card_number} በተሳካ ሁኔታ ተገዝቷል!",
        "card_number": req.card_number,
        "current_balance": user.balance
    }

# 3. 🏆 የጨዋታው ውጤት ሲታወቅ
@router.post("/cards/result")
def process_game_result(req: GameResultRequest, db: Session = Depends(get_db)):
    tg_id_str = str(req.telegram_id).strip()
    
    user = db.query(User).filter(User.telegram_id == tg_id_str).first()
    if not user:
        raise HTTPException(status_code=404, detail="ተጠቃሚው አልተገኘም")
    
    current_balance = getattr(user, "balance", 0.0) or 0.0
    
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
        new_game_record = Game(
            status="finished",
            winner_id=user.id,
            prize=req.win_amount if req.won else 0.0,
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow()
        )
        db.add(new_game_record)
        db.commit()
        db.refresh(user)
    except Exception as e:
        db.rollback()
        print(f"⚠️ ስህተት፦ {e}")
        db.commit()
        
    return {
        "success": True,
        "message": message_detail,
        "won": req.won,
        "updated_balance": user.balance
    }
