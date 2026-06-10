"""
User profile routes: view profile, update own settings.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from config import supabase
from middleware.auth import get_current_user

router = APIRouter()


class SettingsUpdate(BaseModel):
    discord_public: Optional[bool] = None
    job_tab_preference: Optional[bool] = None  # True = open jobs in new tab


@router.get("/{user_id}")
def get_profile(user_id: str, current_user: dict = Depends(get_current_user)):
    """
    Get public profile.
    Discord handle hidden unless public or requesting own profile.
    """
    profile = supabase.table("profiles").select(
        "id, sc_username, discord_handle, discord_public, trust_score, trust_flag, created_at"
    ).eq("id", user_id).maybe_single().execute()

    if not profile.data:
        raise HTTPException(status_code=404, detail="User not found")

    data = profile.data
    is_own = current_user["id"] == user_id

    if not data.get("discord_public") and not is_own:
        data["discord_handle"] = None

    return data


@router.patch("/me/settings")
def update_settings(body: SettingsUpdate, user: dict = Depends(get_current_user)):
    """Update own account preferences."""
    update_data = {k: v for k, v in body.dict().items() if v is not None}
    if not update_data:
        return {"message": "Nothing to update"}

    supabase.table("profiles").update(update_data).eq("id", user["id"]).execute()
    return {"message": "Settings updated"}
