"""
Leaderboard route. Reads from the leaderboard view in Supabase.
"""

from fastapi import APIRouter, Query
from typing import Optional
from config import supabase

router = APIRouter()


@router.get("/")
def get_leaderboard(sort_by: Optional[str] = Query("jobs_completed")):
    """Return leaderboard sorted by chosen column."""
    valid_sorts = {"jobs_completed", "total_earnings", "trust_score"}
    if sort_by not in valid_sorts:
        sort_by = "jobs_completed"

    result = supabase.table("leaderboard").select("*").order(sort_by, desc=True).execute()
    return result.data
