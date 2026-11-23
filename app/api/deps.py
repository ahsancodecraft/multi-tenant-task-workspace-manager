import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from app.core.logging_config import logger
from app.core.security import decode_access_token
from app.db.models import UserModel
from app.db.session import get_db
from app.domain.user import AdminUser

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


def require_admin(current_user: UserModel = Depends(get_current_user)) -> UserModel:
    if current_user.role != "admin":
        logger.warning(f"rbac_admin_denied | user_id={current_user.id} | role={current_user.role}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required",
        )

    admin_domain = AdminUser(
        id=current_user.id,
        email=current_user.email,
        is_active=current_user.is_active,
    )
    if not admin_domain.can_audit_all_tenants():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required",
        )

    return current_user