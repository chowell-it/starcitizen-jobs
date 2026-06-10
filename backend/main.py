"""
Star Citizen Job Board - FastAPI Backend
Entry point. Mounts all routers and configures middleware.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import auth, jobs, users, admin, leaderboard
import os

app = FastAPI(title="SC Job Board", docs_url=None, redoc_url=None, redirect_slashes=False)  # disable public docs in prod

# CORS: restrict to your frontend domain in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(auth.router, prefix="/api/auth")
app.include_router(jobs.router, prefix="/api/jobs")
app.include_router(users.router, prefix="/api/users")
app.include_router(leaderboard.router, prefix="/api/leaderboard")
app.include_router(admin.router, prefix="/api/admin")  # protected server-side, returns 404 if not admin
