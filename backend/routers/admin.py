"""
Admin routes. All protected by require_admin which returns 404 for non-admins.
Non-admins cannot distinguish these routes from nonexistent ones.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from config import supabase
from middleware.auth import require_admin

router = APIRouter()


class ApprovalRequest(BaseModel):
    approved: bool


class UserRoleUpdate(BaseModel):
    role: str  # user / admin


class ForcedStatusUpdate(BaseModel):
    status: str
    failure_reason: Optional[str] = None


@router.get("/jobs/pending")
def get_pending_jobs(admin: dict = Depends(require_admin)):
    """List all jobs awaiting approval (low trust users)."""
    result = supabase.table("jobs").select(
        "*, poster:profiles(sc_username, trust_flag), category:categories(name)"
    ).eq("status", "pending_approval").execute()
    return result.data


@router.patch("/jobs/{job_id}/approve")
def approve_job(job_id: str, body: ApprovalRequest, admin: dict = Depends(require_admin)):
    """Approve or reject a pending job submission."""
    new_status = "open" if body.approved else "failed"
    reason = None if body.approved else "Rejected by admin"

    supabase.table("jobs").update({
        "status": new_status,
        "failure_reason": reason,
    }).eq("id", job_id).execute()

    return {"message": f"Job {'approved' if body.approved else 'rejected'}"}


@router.patch("/jobs/{job_id}/status")
def force_job_status(job_id: str, body: ForcedStatusUpdate, admin: dict = Depends(require_admin)):
    """Force any job into any status. Admin override."""
    update = {"status": body.status}
    if body.failure_reason:
        update["failure_reason"] = body.failure_reason
    supabase.table("jobs").update(update).eq("id", job_id).execute()
    return {"message": "Status updated"}


@router.delete("/jobs/{job_id}")
def delete_job(job_id: str, admin: dict = Depends(require_admin)):
    """Hard delete a job and its members."""
    supabase.table("jobs").delete().eq("id", job_id).execute()
    return {"message": "Job deleted"}


@router.get("/users")
def list_users(admin: dict = Depends(require_admin)):
    """List all users with trust info."""
    result = supabase.table("profiles").select(
        "id, sc_username, discord_handle, role, trust_score, trust_flag, created_at"
    ).execute()
    return result.data


@router.patch("/users/{user_id}/role")
def update_user_role(user_id: str, body: UserRoleUpdate, admin: dict = Depends(require_admin)):
    """Promote or demote a user."""
    if body.role not in ("user", "admin"):
        raise HTTPException(status_code=400, detail="Invalid role")
    supabase.table("profiles").update({"role": body.role}).eq("id", user_id).execute()
    return {"message": f"Role updated to {body.role}"}


@router.delete("/users/{user_id}")
def delete_user(user_id: str, admin: dict = Depends(require_admin)):
    """Delete a user account."""
    supabase.auth.admin.delete_user(user_id)  # removes auth + cascades to profile
    return {"message": "User deleted"}
