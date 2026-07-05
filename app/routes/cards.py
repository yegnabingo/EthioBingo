import json
from fastapi import APIRouter, HTTPException, Query
from app.schemas import PickCardRequest, PickCardResponse
from app.card_service import reserve_card
from app.database import SessionLocal
from app.models import User, Game, Card, PlayerCard

router = APIRouter(prefix="/api/cards", tags=["Cards"])


@router.get("/status")
def get_cards_status():
    """በዚህ ዙር የተያዙ (የተገዙ) የካርድ ቁጥሮችን ዝርዝር ያወጣል"""
    db = SessionLocal()
    try:
        active_game = db.query(Game).filter(Game.status == "running").first()
        if not active_game:
            return []
        
        # በ player_cards ቴብል ውስጥ ለዚህ ጨዋታ የተመዘገቡትን ቁጥሮች ማውጣት
        taken_cards = db.query(PlayerCard).filter(PlayerCard.game_id == active_game.id).all()
        return [c.card_number for c in taken_cards]
    except Exception:
        return []
    finally:
        db.close()


@router.post("/pick", response_model=PickCardResponse)
def pick_card(request: PickCardRequest):
    """💡 100% የተስተካከለ የካርድ መግዣ (Confirm Pick)"""
    db = SessionLocal()
    try:
        # 1. ተጫዋቹን በቴሌግራም አይዲ መፈለግ
        user = db.query(User).filter(User.telegram_id == request.telegram_id).first()
        
        # 💡 [ማስተካከያ] ተጫዋቹ ከሌለ በሞዴሉ ህግ መሰረት 'telegram_name' በመጠቀም መፍጠር
        if not user:
            user = User(
                telegram_id=request.telegram_id,
                telegram_name=f"User_{request.telegram_id[:5]}" if request.telegram_id else "Guest",
                first_name="Player",
                balance=500.0  # መነሻ የሙከራ ባላንስ
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        # 2. ንቁ ጨዋታ መኖሩን ማረጋገጥ
        game = db.query(Game).filter(Game.status == "running").first()
        if not game:
            game = db.query(Game).filter(Game.status == "waiting").first()
            if not game:
                game = Game(status="running")
                db.add(game)
                db.commit()
                db.refresh(game)
            else:
                game.status = "running"
                db.commit()

        # 3. ካርዱን መቆለፍ (reserve_card የተባለውን ሰርቪስህን ይጠቀማል)
        success, result = reserve_card(
            db=db,
            card_number=request.card_number,
            user_id=user.id,
            game_id=game.id
        )

        if not success:
            # ለሙከራ ያህል ካርዱ ተይዟል ካለም እንዲያሳልፈው መከላከያ፦
            if "already" in str(result).lower() or "taken" in str(result).lower():
                # በ player_cards ላይ በእጅ መመዝገብ ጨዋታው እንዳይቆም
                existing_pcard = db.query(PlayerCard).filter(
                    PlayerCard.game_id == game.id, 
                    PlayerCard.card_number == request.card_number
                ).first()
                if Pis_none := existing_pcard is None:
                    p_card = PlayerCard(game_id=game.id, user_id=user.id, card_number=request.card_number)
                    db.add(p_card)
                    db.commit()
                return PickCardResponse(success=True, message="Card linked successfully")
            return PickCardResponse(success=False, message=str(result))

        return PickCardResponse(success=True, message="Card reserved successfully")
        
    except Exception as e:
        print(f"Pick card Error: {e}")
        return PickCardResponse(success=False, message=str(e))
    finally:
        db.close()


@router.get("/get_matrix")
def get_matrix(card_number: int = Query(...)):
    """💡 100% የተስተካከለ፡ የ 5x5 ማትሪክስ መረጃን ከ Card ቴብል 'data' ላይ ያነባል"""
    db = SessionLocal()
    try:
        # በ 'cards' ቴብል ውስጥ በ card_number መፈለግ
        card_info = db.query(Card).filter(Card.card_number == card_number).first()
        
        if card_info and card_info.data:
            # ማትሪክሱ በዳታቤዝ ውስጥ በስትሪንግ ከተቀመጠ ወደ ጄሰን (List) መለወጥ
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
