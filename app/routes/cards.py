from fastapi import APIRouter
from app.schemas import PickCardRequest, PickCardResponse
from app.card_service import reserve_card
from app.database import SessionLocal
from app.models import User, Game

router = APIRouter(prefix="/api/cards", tags=["Cards"])


@router.post("/pick", response_model=PickCardResponse)
def pick_card(request: PickCardRequest):

    db = SessionLocal()

    try:

        user = db.query(User).filter(
            User.telegram_id == request.telegram_id
        ).first()

        if not user:
            return PickCardResponse(
                success=False,
                message="User not found"
            )

        game = db.query(Game).filter(
            Game.status == "running"
        ).first()

        if not game:
            return PickCardResponse(
                success=False,
                message="No active game"
            )

        success, result = reserve_card(
            db=db,
            card_number=request.card_number,
            user_id=user.id,
            game_id=game.id
        )

        if not success:
            return PickCardResponse(
                success=False,
                message=result
            )

        return PickCardResponse(
            success=True,
            message="Card reserved successfully"
        )

    finally:
        db.close()
