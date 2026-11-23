from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import UserModel
from app.db.session import get_db
from app.domain.user import StandardUser
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserPublic,
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    domain_user = StandardUser(id=0, email=payload.email)

    existing = db.query(UserModel).filter(UserModel.email == domain_user.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email address is already registered",
        )

    user_row = UserModel(
        email=domain_user.email,
        password_hash=hash_password(payload.password),
        role=domain_user.role,
    )
    db.add(user_row)
    db.commit()
    db.refresh(user_row)
    return user_row


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    normalized_email = payload.email.strip().lower()
    user = db.query(UserModel).filter(UserModel.email == normalized_email).first()

    if not user or not verify_password(user.password_hash, payload.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(user_id=user.id, role=user.role)
    return TokenResponse(access_token=token)