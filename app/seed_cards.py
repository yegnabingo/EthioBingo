import json

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Card
from app.card_generator import generate_all_cards


def seed_cards():

    db: Session = SessionLocal()

    # Don't create again if cards already exist
    if db.query(Card).count() > 0:
        print("Cards already exist.")
        return

    cards = generate_all_cards()

    for index, card in enumerate(cards, start=1):

        db.add(
            Card(
                card_number=index,
                data=json.dumps(card)
            )
        )

    db.commit()

    print(f"{len(cards)} cards created successfully.")

    db.close()


if __name__ == "__main__":
    seed_cards()
