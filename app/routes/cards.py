from fastapi import APIRouter, HTTPException, Query
from app.schemas import PickCardRequest, PickCardResponse
from app.card_service import reserve_card
from app.database import SessionLocal
from app.models import User, Game
# ⚠️ ማሳሰቢያ፡ በ app/models.py ውስጥ የ Card ቴብል መኖሩን አረጋግጥ
try:
    from app.models import Card
except ImportError:
    Card = None

router = APIRouter(prefix="/api/cards", tags=["Cards"])


@router.get("/status")
def get_cards_status():
    """በዚህ ዙር የተያዙ የካርድ ቁጥሮችን ዝርዝር ያወጣል"""
    db = SessionLocal()
    try:
        active_game = db.query(Game).filter(Game.status == "running").first()
        if not active_game or not Card:
            return []
        
        taken_cards = db.query(Card).filter(Card.game_id == active_game.id).all()
        return [c.card_number for c in taken_cards]
    except Exception:
        return []
    finally:
        db.close()


@router.post("/pick", response_model=PickCardResponse)
def pick_card(request: PickCardRequest):
    """ካርድ መቆለፊያ - ተጫዋቹ ከሌለ በራስ-ሰር ይፈጥረዋል"""
    db = SessionLocal()
    try:
        # 1. ተጫዋቹን መፈለግ
        user = db.query(User).filter(User.telegram_id == request.telegram_id).first()
        
        # 💡 [ዋናው መፍትሄ] ተጫዋቹ ዳታቤዝ ውስጥ ከሌለ እዚሁ ላይ በራስ-ሰር መፍጠር
        if not user:
            user = User(
                telegram_id=request.telegram_id,
                username=f"User_{request.telegram_id[:5]}" if request.telegram_id else "Guest",
                balance=1000.0  # መነሻ የሙከራ ገንዘብ
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        # 2. ንቁ ጨዋታ መኖሩን ማረጋገጥ
        game = db.query(Game).filter(Game.status == "running").first()
        if not game:
            game = Game(status="running")
            db.add(game)
            db.commit()
            db.refresh(game)

        # 3. ካርዱን መቆለፍ (Reserve)
        success, result = reserve_card(
            db=db,
            card_number=request.card_number,
            user_id=user.id,
            game_id=game.id
        )

        if not success:
            return PickCardResponse(success=False, message=result)

        return PickCardResponse(success=True, message="Card reserved successfully")
        
    except Exception as e:
        return PickCardResponse(success=False, message=str(e))
    finally:
        db.close()


@router.get("/get_matrix")
def get_matrix(card_number: int = Query(...)):
    """💡 5x5 ካርድ ከዳታቤዝ ውስጥ ፈልጎ ለተጫዋቹ የሚያሳይ ተግባር"""
    import json
    db = SessionLocal()
    try:
        if not Card:
            raise HTTPException(status_code=500, detail="Card model not found")
            
        # ዳታቤዝ ውስጥ አስቀድሞ በ seed_cards የተፈጠረውን ማትሪክስ መፈለግ
        card_info = db.query(Card).filter(Card.card_number == card_number).first()
        
        if card_info and card_info.matrix:
            # ማትሪክሱ በዳታቤዝ ውስጥ በ String (Text) ከተቀመጠ ወደ JSON (List) መለወጥ
            matrix_data = json.loads(card_info.matrix) if isinstance(card_info.matrix, str) else card_info.matrix
            return {"matrix": matrix_data}
            
        # ካልተገኘ ጨዋታው እንዳይቆም ፎልባክ (Fallback) መስጠት
        import random
        demo_matrix = [[random.randint(1, 75) for _ in range(5)] for _ in range(5)]
        demo_matrix[2][2] = "FREE"
        return {"matrix": demo_matrix}
    finally:
        db.close()
