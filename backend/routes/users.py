from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database.connection import get_db
from schemas.users import UserCreate, UserResponse, UserUpdate
from services.get_auth_id import get_current_user_id
from services.users import create_user, get_user, update_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
def read_me(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    user = get_user(user_id, db)
    if user is None:
        raise HTTPException(status_code=404, detail="Profile not found. Complete onboarding.")
    return user


@router.post("/me", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_me(data: UserCreate, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    return create_user(data, user_id, db)


@router.patch("/me", response_model=UserResponse)
def update_me(data: UserUpdate, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    user = update_user(data, user_id, db)
    if user is None:
        raise HTTPException(status_code=404, detail="Profile not found. Complete onboarding.")
    return user
