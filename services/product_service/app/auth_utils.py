from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import os
from dotenv import load_dotenv
from typing import Union

load_dotenv()

SECRET_KEY: str = os.getenv("JWT_SECRET_KEY") or ""
if not SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY environment variable is not set")

ALGORITHM = "HS256"
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Union[str, None]:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        user_email = payload.get("email")
        user_id = payload.get("userId")
        role = payload.get("role")
        role_id = payload.get("roleId")

        if not role or role.lower() == "enduser":
            raise HTTPException(
                status_code=403, detail="Access forbidden: Admins only"
            )

        if user_email:
            return user_email
        else:
            raise HTTPException(status_code=401, detail="Invalid token payload")

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")