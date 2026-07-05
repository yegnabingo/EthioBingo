from fastapi import APIRouter, Depends
from app.schemas import PickCardRequest, PickCardResponse
from app.card_service import reserve_card
from app.database import SessionLocal
from app.models import User, Game, Card # Card ሞዴል ካለህ አስገባው
from fastapi.responses import JSONResponse
import json

router = APIRouter(prefix="/api/cards", tags=["Cards"])

@router.get("/status")
def get_cards_status():
    """
    1. የ 404 ስህተቱን የሚፈታው ዋናው ተግባር!
    በአሁኑ ሰዓት በነጻነት ላይ ያሉ እና የተያዙ (Locked) ካርዶችን ዝርዝር ከዳታቤዝ ያወጣል
    """
    db = SessionLocal()
    try:
        active_game = db.query(Game).filter(Game.status == "running").first()
        if not active_game:
            return [] # ንቁ ጨዋታ ከሌለ ሁሉንም ካርዶች ክፍት አድርግ
            
        # በዚህ ጨዋታ ውስጥ የተያዙ የካርድ ቁጥሮችን ብቻ ማውጣት
        # ማሳሰቢያ: በሞዴልህ መሰረት Card ወይም CardSelection ቴብልህን ተጠቀም
        taken_cards = db.query(Card).filter(Card.game_id == active_game.id).all()
        return [c.card_number for c in taken_cards]
    except Exception as e:
        print(f"Error fetching card status: {e}")
        return []
    finally:
        db.close()


@router.post("/pick", response_model=PickCardResponse)
def pick_card(request: PickCardRequest):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == request.telegram_id).first()
        if not user:
            return PickCardResponse(success=False, message="User not found")

        game = db.query(Game).filter(Game.status == "running").first()
        if not game:
            return PickCardResponse(success=False, message="No active game")

        success, result = reserve_card(
            db=db,
            card_number=request.card_number,
            user_id=user.id,
            game_id=game.id
        )

        if not success:
            return PickCardResponse(success=False, message=result)

        return PickCardResponse(success=True, message="Card reserved successfully")
    finally:
        db.close()


@router.get("/get_matrix")
def get_matrix(card_number: int):
    """
    2. የተጫዋቹን እውነተኛ የ 5x5 የቢንጎ ማትሪክስ ከዳታቤዝ አውጥቶ ለጃቫስክሪፕቱ የሚሰጥ
    """
    db = SessionLocal()
    try:
        # ዳታቤዝ ውስጥ ካርዶቹ አስቀድመው ተፈጥረው ማትሪክሳቸው በ JSON ከተቀመጠ፡
        card_info = db.query(Card).filter(Card.card_number == card_number).first()
        if card_info and card_info.matrix:
            # ማትሪክሱ በስትሪንግ ከተቀመጠ ወደ ሊስት ለመቀየር json.loads ተጠቀም
            matrix_data = json.loads(card_info.matrix) if isinstance(card_info.matrix, str) else card_info.matrix
            return {"matrix": matrix_data}
            
        # ካልተገኘ ግን ዲሞ ማትሪክስ በነጻነት ይሰጠው (ጨዋታው እንዳይቆም)
        import random
        demo_matrix = [[random.randint(1,75) for _ in range(5)] for _ in range(5)]
        demo_matrix[2][2] = "FREE"
        return {"matrix": demo_matrix}
    finally:
        db.close()

