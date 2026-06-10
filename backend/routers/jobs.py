"""
Jobs routes: list, get, create, accept, update status, submit rating.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from config import supabase
from middleware.auth import get_current_user

router = APIRouter()


@router.get("/categories")
def get_categories():
    """Return all job categories. Public endpoint."""
    result = supabase.table("categories").select("id, name").order("name").execute()
    return result.data


class JobCreateRequest(BaseModel):
    title: str
    category_id: str
    difficulty: str  # Easy / Medium / Hard / Extreme
    pay_auec: int
    description: Optional[str] = None
    slots_total: int = 1
    expires_at: Optional[datetime] = None


class StatusUpdateRequest(BaseModel):
    status: str
    failure_reason: Optional[str] = None


class RatingRequest(BaseModel):
    ratee_id: str
    stars: int


@router.get("/")
def list_jobs(
    category: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("created_at"),
):
    """List jobs with optional filters. Public endpoint."""
    query = supabase.table("jobs").select(
        "*, poster:profiles(sc_username, trust_flag), category:categories(name)"
    )

    if category:
        query = query.eq("category_id", category)
    if difficulty:
        query = query.eq("difficulty", difficulty)
    if status:
        query = query.eq("status", status)
    else:
        # Default: exclude pending approval and completed/failed from main board
        query = query.not_.in_("status", ["pending_approval", "completed", "failed"])

    result = query.order(sort_by, desc=True).execute()
    return result.data


@router.get("/{job_id}")
def get_job(job_id: str, user: dict = Depends(get_current_user)):
    """
    Get single job detail.
    Discord handle revealed only to accepted members or if poster set discord_public.
    """
    job = supabase.table("jobs").select(
        "*, poster:profiles(id, sc_username, trust_flag, discord_handle, discord_public), "
        "category:categories(name), members:job_members(user_id, is_leader, profiles(sc_username, trust_flag))"
    ).eq("id", job_id).single().execute()

    if not job.data:
        raise HTTPException(status_code=404, detail="Job not found")

    data = job.data
    poster = data.get("poster", {})

    # Hide discord unless public preference or user is a member
    member_ids = [m["user_id"] for m in (data.get("members") or [])]
    is_member = user["id"] in member_ids or user["id"] == poster.get("id")
    if not poster.get("discord_public") and not is_member:
        poster["discord_handle"] = None

    return data


@router.post("/")
def create_job(body: JobCreateRequest, user: dict = Depends(get_current_user)):
    """
    Create a new job. One active post per user enforced.
    Low trust users enter pending_approval status.
    """
    if user.get("active_post_id"):
        raise HTTPException(status_code=400, detail="You already have an active job posting")

    status = "pending_approval" if user["trust_flag"] == "low" else "open"

    result = supabase.table("jobs").insert({
        "poster_id": user["id"],
        "title": body.title,
        "category_id": body.category_id,
        "difficulty": body.difficulty,
        "pay_auec": body.pay_auec,
        "description": body.description,
        "slots_total": body.slots_total,
        "expires_at": body.expires_at.isoformat() if body.expires_at else None,
        "status": status,
    }).execute()

    job_id = result.data[0]["id"]

    # Track poster's active post
    supabase.table("profiles").update({"active_post_id": job_id}).eq("id", user["id"]).execute()

    # Poster is automatically the leader/first member
    supabase.table("job_members").insert({
        "job_id": job_id,
        "user_id": user["id"],
        "is_leader": True,
    }).execute()

    return result.data[0]


@router.post("/{job_id}/accept")
def accept_job(job_id: str, user: dict = Depends(get_current_user)):
    """Join a job as a member. One active acceptance per user enforced."""
    if user.get("active_accept_id"):
        raise HTTPException(status_code=400, detail="You are already on an active job")

    job = supabase.table("jobs").select("*").eq("id", job_id).single().execute()
    if not job.data:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.data["status"] not in ("open", "partial"):
        raise HTTPException(status_code=400, detail="Job is not accepting members")

    if job.data["poster_id"] == user["id"]:
        raise HTTPException(status_code=400, detail="You cannot accept your own job")

    supabase.table("job_members").insert({
        "job_id": job_id,
        "user_id": user["id"],
        "is_leader": False,
    }).execute()

    supabase.table("profiles").update({"active_accept_id": job_id}).eq("id", user["id"]).execute()

    return {"message": "Joined job successfully"}


@router.patch("/{job_id}/status")
def update_job_status(job_id: str, body: StatusUpdateRequest, user: dict = Depends(get_current_user)):
    """
    Update job status. Only poster or admin can update.
    Failed status requires a reason.
    """
    job = supabase.table("jobs").select("poster_id").eq("id", job_id).single().execute()
    if not job.data:
        raise HTTPException(status_code=404, detail="Job not found")

    is_poster = job.data["poster_id"] == user["id"]
    is_admin = user["role"] == "admin"

    if not is_poster and not is_admin:
        raise HTTPException(status_code=403, detail="Forbidden")

    if body.status == "failed" and not body.failure_reason:
        raise HTTPException(status_code=400, detail="Failure reason required")

    update_data = {"status": body.status}
    if body.failure_reason:
        update_data["failure_reason"] = body.failure_reason

    # Clear active tracking on terminal states
    if body.status in ("completed", "failed"):
        members = supabase.table("job_members").select("user_id").eq("job_id", job_id).execute()
        for m in members.data:
            supabase.table("profiles").update({"active_accept_id": None, "active_post_id": None}).eq("id", m["user_id"]).execute()

    supabase.table("jobs").update(update_data).eq("id", job_id).execute()
    return {"message": f"Job marked as {body.status}"}


@router.post("/{job_id}/rate")
def rate_user(job_id: str, body: RatingRequest, user: dict = Depends(get_current_user)):
    """Submit a rating after job completion. One rating per pair per job."""
    job = supabase.table("jobs").select("status").eq("id", job_id).single().execute()
    if not job.data or job.data["status"] != "completed":
        raise HTTPException(status_code=400, detail="Can only rate after job is completed")

    if not (1 <= body.stars <= 5):
        raise HTTPException(status_code=400, detail="Stars must be 1-5")

    try:
        supabase.table("ratings").insert({
            "job_id": job_id,
            "rater_id": user["id"],
            "ratee_id": body.ratee_id,
            "stars": body.stars,
        }).execute()
    except Exception:
        raise HTTPException(status_code=400, detail="Already rated this user for this job")

    return {"message": "Rating submitted"}
