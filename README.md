# UEE Operations — Star Citizen Job Board

## Stack
- Frontend: HTML + CSS + Vanilla JS (Vercel)
- Backend: FastAPI (Vercel serverless or self-hosted)
- Database + Auth: Supabase (free tier)

---

## Setup

### 1. Supabase
1. Create a free project at https://supabase.com
2. Go to SQL Editor and run the full contents of `supabase/schema.sql`
3. Copy your project URL and service role key from Settings > API

### 2. Backend
```bash
cd backend
cp .env.example .env
# Fill in SUPABASE_URL and SUPABASE_SERVICE_KEY in .env

pip install -r requirements.txt
uvicorn main:app --reload
```
Backend runs at http://localhost:8000

### 3. Frontend
Serve the `frontend/` folder with any static server. For local dev:
```bash
cd frontend
npx serve .
```
Or open index.html directly — update `API_BASE` in `js/api.js` to match your backend URL.

### 4. Deploying
- **Frontend**: Push to GitHub, connect repo to Vercel, set root to `frontend/`
- **Backend**: Deploy to Railway, Render, or your own VPS. Set env vars in the dashboard.
- Update `API_BASE` in `frontend/js/api.js` and `FRONTEND_URL` in backend `.env` to production URLs.

---

## Creating the first admin
1. Register an account normally through the UI
2. In Supabase dashboard > Table Editor > profiles
3. Find your user row and change `role` from `user` to `admin`

---

## Project Structure
```
starcitizen-jobs/
├── frontend/
│   ├── index.html          # Job board dashboard
│   ├── css/main.css        # Global styles
│   ├── js/
│   │   ├── api.js          # All backend API calls
│   │   └── ui.js           # Shared nav, toast, badge helpers
│   └── pages/
│       ├── job.html        # Job detail
│       ├── login.html      # Login / register
│       ├── submit.html     # Post a job
│       ├── leaderboard.html
│       ├── profile.html    # Profile + settings
│       └── admin.html      # Admin panel
├── backend/
│   ├── main.py             # FastAPI entry point
│   ├── config.py           # Supabase client
│   ├── requirements.txt
│   ├── middleware/
│   │   └── auth.py         # JWT validation, require_admin (returns 404)
│   └── routers/
│       ├── auth.py         # Register, login
│       ├── jobs.py         # Job CRUD, accept, status, ratings
│       ├── users.py        # Profile, settings
│       ├── leaderboard.py
│       └── admin.py        # Admin-only routes
└── supabase/
    └── schema.sql          # Full DB schema, RLS policies, triggers, seed data
```
