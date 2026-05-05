from fastapi import Depends, HTTPException
from app.auth.utils import get_current_user


def role_required(required_roles: list):

    def checker(user=Depends(get_current_user)):

        if user["role"] not in required_roles:
            raise HTTPException(
                status_code=403,
                detail="Permission denied"
            )

        return user

    return checker