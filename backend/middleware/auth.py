"""
Auth middleware.
Validates Supabase JWT from Authorization header.
Provides get_current_user and require_admin dependencies.
"""

from fastapi import Depends, HTTPException, Header
from typing import Optional
from config import supabase


def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """Validate JWT from Authorization header and return user profile."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")

    token = authorization.split(" ", 1)[1]

    try:
        user_resp = supabase.auth.get_user(token)
        if not user_resp or not user_resp.user:
            raise HTTPException(status_code=401, detail="Invalid token")

        uid = user_resp.user.id
        profile = supabase.table("profiles").select("*").eq("id", uid).single().execute()
        if not profile.data:
            raise HTTPException(status_code=401, detail="Profile not found")

        return profile.data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Auth error: {str(e)}")


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """Returns 404 for non-admin users to prevent endpoint enumeration."""
    if user.get("role") != "admin":
        raise HTTPException(status_code=404, detail="Not found")
    return user