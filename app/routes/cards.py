import json
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from app.database import SessionLocal
from app.models import User, Game, Card, PlayerCard

router = APIRouter(prefix="/api/cards", tags=["Cards"])

# 📝 ለካርድ መግዣ ጥያቄ የሚመጣ ዳታ ፎርማት (Schema)
class AdvancedPickCardRequest(BaseModel):
    telegram_id: str
    card_number: int
    bet_amount: float = Field(..., description="የውርርድ መጠን፡ 10, 20, ወይም 50")

@router.get("/status")
def get_cards_status():
    """በዚህ ዙር የተገዙ የካርድ ቁጥሮችን ዝርዝር ለሁሉም ያሳያል"""
    db = SessionLocal()
    try:
        active_game = db.query(Game).filter(Game.status == "running").first()
        if not active_game:
            return []
        
        taken_cards = db.query(PlayerCard).filter(PlayerCard.game_id == active_game.id).all()
        return [c.card_number for c in taken_cards]
    except Exception:
        return []
    finally:
        db.close()


@router.post("/pick")
def pick_card(request: AdvancedPickCardRequest):
    """
    🎯 100% የተስተካከለ የካርድ መግዣ ሎጂክ፦
    1. የተጫዋች ባላንስ ይፈትሻል (10, 20, 50 ብር)
    2. በአንድ ዙር ከ 5 ካርድ በላይ እንዳይገዛ ይከለክላል (One-by-One)
    3. ብር ቀንሶ በ player_cards ላይ ይመዘግባል
    """
    db = SessionLocal()
    try:
        # 1. ውርርዱ የተፈቀደ መሆኑን ማረጋገጥ (10, 20, 50 ብር ብቻ)
        if request.bet_amount not in [10.0, 20.0, 50.0]:
            return {"success": False, "message": "ያልተፈቀደ የውርርድ መጠን! እባክህ 10፣ 20 ወይም 50 ይምረጡ።"}

        # 2. ተጫዋቹን በቴሌግራም አይዲ መፈለግ
        user = db.query(User).filter(User.telegram_id == request.telegram_id).first()
        if not user:
            # ለሙከራ እንዲያመች ተጫዋቹ ከሌለ በ500 ብር መነሻ ባላንስ መፍጠር
            user = User(
                telegram_id=request.telegram_id,
                telegram_name=f"User_{request.telegram_id[:5]}" if request.telegram_id else "Guest",
                first_name="Player",
                balance=500.0
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        # 3. ንቁ ጨዋታ መኖሩን ማረጋገጥ
        game = db.query(Game).filter(Game.status == "running").first()
        if not game:
            return {"success": False, "message": "በአሁኑ ሰዓት ምንም የነቃ ጨዋታ የለም። እባክህ አዲስ ዙር ጠብቅ።"}

        # 4. የ 5 ካርድ ገደብ ፍተሻ (Max 5 Cards Check)
        already_bought_count = db.query(PlayerCard).filter(
            PlayerCard.game_id == game.id,
            PlayerCard.user_id == user.id
        ).count()
        
        if already_bought_count >= 5:
            return {"success": False, "message": "በአንድ ጨዋታ መግዛት የሚችሉት ከፍተኛው የካርድ መጠን 5 ብቻ ነው!"}

        # 5. የካርዱ ቁጥር አስቀድሞ መያዙን ማረጋገጥ
        card_taken = db.query(PlayerCard).filter(
            PlayerCard.game_id == game.id,
            PlayerCard.card_number == request.card_number
        ).first()
        if card_taken:
            return {"success": False, "message": f"ካርድ ቁጥር {request.card_number} አስቀድሞ በሌላ ተጫዋች ተይዟል!"}

        # 5. የካርዱ ቁጥር አስቀድሞ መያዙን ማረጋገጥ
        card_taken = db.query(PlayerCard).filter(
            PlayerCard.game_id == game.id,
            PlayerCard.card_number == request.card_number
        ).first()

        if card_taken:
            return {"success": False, "message": f"ካርድ ቁጥር {request.card_number} አስቀድሞ በሌላ ተጫዋች ተይዟል!"}
 
        # 6. የባላንስ ፍተሻ (Balance Check)
        if user.balance < request.bet_amount:
            return {"success": False, "message": f"ቂ ባላንስ የሎትም! የእርሶ ባላንስ {user.balance} ETB ነው።"}

        # 7. ክፍያውን መቁረጥ (Deduct Balance)
        user.balance -= request.bet_amount
        
        # 8. ካርዱን ለተጫዋቹ መመዝገብ
        new_player_card = PlayerCard(
            game_id=game.id,
            user_id=user.id,
            card_number=request.card_number
            # ማሳሰቢያ፡ እውነተኛ የውርርድ መጠን በሞዴልሽ ላይ እንዲቀመጥ የጨዋታውን ጠቅላላ ገቢ በ main.py እናሳድገዋለን
        )
        db.add(new_player_card)
        db.commit()

        print(f"💰 ተጫዋች {user.telegram_id} ካርድ #{request.card_number} በ {request.bet_amount} ብር ገዝቷል። ቀሪ ባላንስ: {user.balance}")
        return {"success": True, "message": "ካርዱ በተሳካ ሁኔታ ተገዝቷል!", "current_balance": user.balance}
        
    except Exception as e:
        db.rollback()
        print(f"Pick card Error: {e}")
        return {"success": False, "message": f"የቴክኒክ ስህተት አጋጥሟል፡ {str(e)}"}
    finally:
        db.close()


@router.get("/get_matrix")
def get_matrix(card_number: int = Query(...)):
    """💡 የ 5x5 ማትሪክስ መረጃን ከ Card ቴብል 'data' ላይ ያነባል"""
    db = SessionLocal()
    try:
        card_info = db.query(Card).filter(Card.card_number == card_number).first()
        
        if card_info and card_info.data:
            try:
                matrix_data = json.loads(card_info.data)
                return {"matrix": matrix_data}
            except Exception:
                pass
                
        # 🎯 [ፎልባክ] በዳታቤዝ ውስጥ ካርዱ በዘርፍ ካልተገኘ እውነተኛ የቢንጎ ማትሪክስ ሰርቶ ይሰጠዋል
        import random
        b = random.sample(range(1, 16), 5)
        i = random.sample(range(16, 30), 5)
        n = random.sample(range(31, 45), 5)
        g = random.sample(range(46, 60), 5)
        o = random.sample(range(61, 75), 5)
        
        generated_matrix = []
        for r_idx in range(5):
            row = [b[r_idx], i[r_idx], n[r_idx], g[r_idx], o[r_idx]]
            generated_matrix.append(row)
            
        generated_matrix[2][2] = "FREE" # መሃል ቁጥር ነጻ ናት
        return {"matrix": generated_matrix}
        
    except Exception as e:
        return {"matrix": [[i for i in range(5)] for _ in range(5)]}
    finally:
        db.close()
