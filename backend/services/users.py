from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from models.user import User
from schemas.users import UserCreate, UserUpdate

REQUIRED_FIELDS = {"name", "shop_name"}

def get_user(user_id: str, db: Session) -> User | None:
    """Find the profile whose id is the verified Better Auth user ID."""
    return db.get(User, user_id)

def create_user(data: UserCreate, user_id: str, db: Session) -> User:
    """Create the profile once. If it already exists, return it unchanged."""
    existing_user = get_user(user_id, db)
    if existing_user:
        return existing_user

    new_user = User(
        id=user_id,
        name=data.name,
        shop_name=data.shop_name,
        shop_category=data.shop_category,
    )

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user
    except IntegrityError:
        db.rollback()
        existing_user = get_user(user_id, db)
        if existing_user:
            return existing_user
        raise
    except SQLAlchemyError:
        db.rollback()
        raise

def update_user(data: UserUpdate, user_id: str, db: Session) -> User | None:
    user = get_user(user_id, db)
    if user is None:
        return None

    update_data = data.model_dump(exclude_unset=True)

    try:
        for key, value in update_data.items():
            if value is None and key in REQUIRED_FIELDS:
                continue
            setattr(user, key, value)

        db.commit()
        db.refresh(user)
        return user
    except SQLAlchemyError:
        db.rollback()
        raise
