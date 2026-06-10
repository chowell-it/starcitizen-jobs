"""
Auth routes: register, login.
Supabase handles password hashing and session tokens.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional
from config import supabase

router = APIRouter()


class RegisterRequest(BaseModel):
    sc_username: str
    discord_handle: str
    password: str
    email: Optional[EmailStr] = None  # optional for recovery only


class LoginRequest(BaseModel):
    sc_username: str
    password: str


@router.post("/register")
def register(body: RegisterRequest):
    """Register new user. Uses sc_username as display identity."""
    # Use a synthetic email for Supabase auth if no real email provided
    auth_email = body.email or f"{body.sc_username}@scjobboard.internal"

    try:
        result = supabase.auth.sign_up({
            "email": auth_email,
            "password": body.password,
            "options": {
                "data": {
                    "sc_username": body.sc_username,
                    "discord_handle": body.discord_handle,
                }
            }
        })
        if result.user is None:
            raise HTTPException(status_code=400, detail="Registration failed")
        return {"message": "Registered successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
def login(body: LoginRequest):
    """Login with sc_username and password. Returns JWT session token."""
    # Look up auth email from sc_username
    profile = supabase.table("profiles").select("id, email").eq("sc_username", body.sc_username).maybe_single().execute()
    if not profile.data:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    auth_email = profile.data.get("email") or f"{body.sc_username}@scjobboard.internal"

    try:
        result = supabase.auth.sign_in_with_password({
            "email": auth_email,
            "password": body.password
        })
        if not result.session:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return {
            "access_token": result.session.access_token,
            "user": {
                "id": result.user.id,
                "sc_username": body.sc_username,
            }
        }
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid credentials")
