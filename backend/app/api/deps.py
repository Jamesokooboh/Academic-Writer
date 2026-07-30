from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import InvalidTokenError, decode_access_token
from app.db.models import User
from app.db.session import get_db

_bearer = HTTPBearer(auto_error=True)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    try:
        user_id = decode_access_token(credentials.credentials)
    except InvalidTokenError:
        raise unauthorized
    user = db.execute(select(User).where(User.id == int(user_id))).scalar_one_or_none()
    if user is None:
        raise unauthorized
    return user
