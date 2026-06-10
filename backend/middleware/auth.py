"""
Auth middleware.
Validates Supabase JWT from Authorization header.
Provides get_current_user and require_admin dependencies.
"""

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config import supabase

bearer = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> dict:
    """Validate JWT and return user profile. Raises 401 if invalid."""
    token = credentials.credentials
    try:
        # Verify token with Supabase — role comes from DB, never from client payload
        user_resp = supabase.auth.get_user(token)
        if not user_resp.user:
            raise HTTPException(status_code=401, detail="Invalid token")

        uid = user_resp.user.id
        profile = supabase.table("profiles").select("*").eq("id", uid).single().execute()
        if not profile.data:
            raise HTTPException(status_code=401, detail="Profile not found")

        return profile.data
    except Exception:
        raise HTTPException(status_code=401, detail="Unauthorized")


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """
    Returns 404 (not 403) for non-admin users.
    Prevents endpoint enumeration — appears as if route does not exist.
    """
    if user.get("role") != "admin":
        raise HTTPException(status_code=404, detail="Not found")
    return user
