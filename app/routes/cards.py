import json
import random
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from app.database import SessionLocal
from app.models import User, Game, Card, PlayerCard
from app.websocket_manager import manager # 📡 የካርድ መገዛትን ለሁሉም ላይቭ ለማሳየት

router = APIRouter(prefix="/api/cards", tags=["Cards"])

# 📝 ለካርድ መግዣ ጥያቄ የሚመጣ ዳታ ፎርማት (Schema)
class AdvancedPickCardRequest(BaseModel):
    telegram_id: str
    card_number: int
    bet_amount: float = Field(..., description="የውርርድ መጠን፡ 10, 20, ወይም 50")

@router.get("/status")
def get_cards_status(bet_amount: float = Query(10.0, description="የተመረጠው ክፍል ውርርድ መጠን")):
    """
    🛠️ ማሻሻያ፦ በአሁኑ ሰዓት ንቁ እና ገና በዝግጅት ላይ ያለ (waiting) ጨዋታ ካለ ብቻ የተገዙ ካርዶችን ያሳያል።
    አዲስ ጨዋታ ሲጀምር የድሮ ጨዋታ ካርዶች እንዳይታዩ እና ሰሌዳው ነጭ እንዲሆን ተደርጓል።
    """
    db = SessionLocal()
    try:
        # 🎯 ፍጹም ማስተካከያ፦ በጣም የቅርብ ጊዜውን የነቃ ጨዋታ ያነባል።
        active_game = db.query(Game).order_by(Game.id.desc()).first()
        
        # ጨዋታ ከሌለ ወይም ጨዋታው አልቆ 'finished' ከሆነ ሰሌዳው ሙሉ በሙሉ ነጭ እንዲሆን ባዶ ዝርዝር [] ይመልሳል
        if not active_game or active_game.status == "finished":
            return []
            
        # 💡 ጨዋታው ገና ተጀምሮ በቆጠራ (waiting) ላይ ከሆነ ወይም እየተጫወቱ (running) ከሆነ ብቻ የተገዙትን ያሳያል
        taken_cards = db.query(PlayerCard).filter(
            PlayerCard.game_id == active_game.id,
            PlayerCard.bet_amount == bet_amount
        ).all()
        return [c.card_number for c in taken_cards]
    except Exception:
        return []
    finally:
        db.close()


@router.post("/pick")
async def pick_card(request: AdvancedPickCardRequest):
    """
    🎯 100% ከተስተካከለው የጌም ኢንጂን ጋር የተጣጣመ የካርድ መግዣ ሎጂክ
    🎁 የተሻሻለ፦ ክፍያ ሲፈጸም ቅድሚያ ከ Gift Coin (መጫወቻ ቦነስ) ላይ ይቀንሳል
    """
    db = SessionLocal()
    try:
        # 1. ውርርዱ የተፈቀደ መሆኑን ማረጋገጥ (10, 20, 50 ብር ብቻ)
        if request.bet_amount not in [10.0, 20.0, 50.0]:
            return {"success": False, "message": "ያልተፈቀደ የውርርድ መጠን! እባክህ 10፣ 20 ወይም 50 ይምረጡ።"}

        # 2. ተጫዋቹን በቴሌግራም አይዲ መፈለግ
        user = db.query(User).filter(User.telegram_id == request.telegram_id).first()
        if not user:
            user = User(
                telegram_id=request.telegram_id,
                telegram_name=f"User_{request.telegram_id[:5]}" if request.telegram_id else "Guest",
                first_name="Player",
                balance=0.0,
                wallet=0.0,
                gift_coin=0.0
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        # 3. ንቁ ጨዋታ መኖሩን ማረጋገጥ (ማሳሰቢያ፦ ጨዋታው ገና ሲጀምር status 'waiting' ሊሆን ስለሚችል ሁለቱንም ይፈትሻል)
        game = db.query(Game).filter(Game.status.in_(["running", "waiting"])).order_by(Game.id.desc()).first()
        if not game:
            return {"success": False, "message": "በአሁኑ ሰዓት ምንም የነቃ ጨዋታ የለም። እባክህ አዲስ ዙር ጠብቅ።"}

        # 4. የ 5 ካርድ ገደብ ፍተሻ (Max 5 Cards Check)
        already_bought_count = db.query(PlayerCard).filter(
            PlayerCard.game_id == game.id,
            PlayerCard.user_id == user.id
        ).count()
        
        if already_bought_count >= 5:
            return {"success": False, "message": "በአንድ ጨዋታ መግዛት የሚችሉት ከፍተኛው የካርድ መጠን 5 ብቻ ነው!"}

        # 5. የካርዱ ቁጥር በዚሁ ክፍል (Bet Room) አስቀድሞ መያዙን ማረጋገጥ
        card_taken = db.query(PlayerCard).filter(
            PlayerCard.game_id == game.id,
            PlayerCard.card_number == request.card_number,
            PlayerCard.bet_amount == request.bet_amount
        ).first()
        if card_taken:
            return {"success": False, "message": f"ካርድ ቁጥር {request.card_number} በ {int(request.bet_amount)} ብር ክፍል አስቀድሞ ተይዟል!"}
 
        # 6. የባላንስ ፍተሻ (Balance Check) - ጠቅላላ ባላንስ = ዋና ባላንስ + መጫወቻ ቦነስ (Gift Coin)
        total_available = (user.balance or 0.0) + (user.gift_coin or 0.0)
        if total_available < request.bet_amount:
            return {"success": False, "message": f"በቂ ባላንስ የሎትም! የእርሶ ጠቅላላ ባላንስ {total_available} ETB ነው።"}

        # 7. ክፍያውን የመቁረጥ ሎጂክ (ቅድሚያ ለ Gift Coin መስጠት)
        if (user.gift_coin or 0.0) >= request.bet_amount:
            user.gift_coin -= request.bet_amount
        else:
            remaining_fee = request.bet_amount - (user.gift_coin or 0.0)
            user.gift_coin = 0.0
            user.balance -= remaining_fee
            user.wallet -= remaining_fee  
        
        # 8. ካርዱን ለተጫዋቹ መመዝገብ
        new_player_card = PlayerCard(
            game_id=game.id,
            user_id=user.id,
            card_number=request.card_number,
            bet_amount=request.bet_amount
        )
        db.add(new_player_card)

        main_card = db.query(Card).filter(Card.card_number == request.card_number).first()
        if main_card:
            main_card.is_taken = True
            main_card.reserved_by = user.id
            main_card.current_game_id = game.id
        
        # 🎯 🔴 አዲስ የተጨመረ፦ የተጫዋቹን አጠቃላይ እና ሳምንታዊ የካርድ ቆጣሪዎች መደመር
        user.total_games_played = (getattr(user, "total_games_played", 0) or 0) + 1
        user.weekly_games_played = (getattr(user, "weekly_games_played", 0) or 0) + 1

        db.commit()

        try:
            all_taken = db.query(PlayerCard).filter(PlayerCard.game_id == game.id).all()
            taken_list = [c.card_number for c in all_taken]
            await manager.broadcast({
                "type": "taken_cards_update",
                "bet_amount": request.bet_amount,
                "taken_cards": taken_list
            })
        except Exception as e:
            print(f"⚠️ Live broadcast failed after pick: {e}")

        print(f"💰 ተጫዋች {user.telegram_id} ካርድ #{request.card_number} በ {request.bet_amount} ብር ገዝቷል። ቀሪ ባላንስ: {user.balance}, Gift: {user.gift_coin}")
        return {
            "success": True, 
            "message": "ካርዱ በተሳካ ሁኔታ ተገዝቷል!", 
            "current_balance": user.balance,
            "current_gift": user.gift_coin,
            "card_number": request.card_number,
            "bet_amount": request.bet_amount
        }
        
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
                
        b = random.sample(range(1, 16), 5)
        i = random.sample(range(16, 31), 5)
        n = random.sample(range(31, 46), 5)
        g = random.sample(range(46, 61), 5)
        o = random.sample(range(61, 76), 5)
        
        generated_matrix = []
        for r_idx in range(5):
            row = [b[r_idx], i[r_idx], n[r_idx], g[r_idx], o[r_idx]]
            generated_matrix.append(row)
            
        generated_matrix[2][2] = "FREE"
        return {"matrix": generated_matrix}
        
    except Exception as e:
        return {"matrix": [[i for i in range(5)] for _ in range(5)]}
    finally:
        db.close()
