from sqlalchemy.orm import Session

from app.models import Card


def reserve_card(db: Session, card_number: int, user_id: int, game_id: int):

    card = db.query(Card).filter(
        Card.card_number == card_number
    ).first()

    if card is None:
        return False, "Card not found"

    if card.is_taken:
        return False, "Card already taken"

    card.is_taken = True
    card.current_game_id = game_id
    card.reserved_by = user_id

    db.commit()

    return True, card
