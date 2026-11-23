import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from app.core.security import decode_access_token
from app.db.models import UserModel
from app.db.session import get_db

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> UserModel:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing, invalid, or expired authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized

    try:
        payload = decode_access_token(credentials.credentials)
        sub = payload.get("sub")
        if sub is None:
            raise unauthorized
        user_id = int(sub)
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, ValueError):
        raise unauthorized

    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if user is None or not user.is_active:
        raise unauthorized
    return user