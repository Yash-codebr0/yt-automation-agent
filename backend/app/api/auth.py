from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import get_password_hash, verify_password, create_access_token
from backend.app.models.user import User
from backend.app.schemas.user import UserCreate, UserOut, Token, UserLogin
from backend.app.api.deps import get_current_user

router = APIRouter()

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    # Check if user exists
    db_user = db.query(User).filter(User.email == user_in.email).first()
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="A user with this email already exists."
        )
    
    # Create user
    user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        role="creator"  # Default role
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.post("/login", response_model=Token)
def login(
    user_in: UserLogin,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == user_in.email).first()
    if not user or not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
        
    access_token = create_access_token(subject=user.id)
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserOut)
def read_user_me(current_user: User = Depends(get_current_user)):
    return current_user
