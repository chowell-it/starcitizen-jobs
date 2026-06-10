-- ============================================================
-- Star Citizen Job Board - Supabase Schema
-- Run this in Supabase SQL editor to initialize the database
-- ============================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- TABLES
-- ============================================================

-- Users (extends Supabase auth.users)
CREATE TABLE public.profiles (
    id UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
    sc_username TEXT UNIQUE NOT NULL,
    discord_handle TEXT NOT NULL,
    email TEXT,
    role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    trust_score NUMERIC(3,2) DEFAULT 3.0,
    trust_flag TEXT DEFAULT 'normal' CHECK (trust_flag IN ('low', 'normal', 'high')),
    discord_public BOOLEAN DEFAULT FALSE,   -- user preference: show discord to all
    job_tab_preference BOOLEAN DEFAULT TRUE, -- user preference: open jobs in new tab
    active_post_id UUID,                    -- tracks user's one active job post
    active_accept_id UUID,                  -- tracks user's one active job acceptance
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Job categories
CREATE TABLE public.categories (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

-- Jobs
CREATE TABLE public.jobs (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    poster_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    category_id UUID REFERENCES public.categories(id),
    difficulty TEXT NOT NULL CHECK (difficulty IN ('Easy', 'Medium', 'Hard', 'Extreme')),
    pay_auec BIGINT NOT NULL DEFAULT 0,
    description TEXT,
    slots_total INT NOT NULL DEFAULT 1 CHECK (slots_total BETWEEN 1 AND 10),
    slots_filled INT NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'partial', 'full', 'in_progress', 'completed', 'failed', 'pending_approval')),
    failure_reason TEXT,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Job members (accepted users per job)
CREATE TABLE public.job_members (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    job_id UUID REFERENCES public.jobs(id) ON DELETE CASCADE,
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    is_leader BOOLEAN DEFAULT FALSE,
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(job_id, user_id)
);

-- Ratings (submitted after job completion)
CREATE TABLE public.ratings (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    job_id UUID REFERENCES public.jobs(id) ON DELETE CASCADE,
    rater_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    ratee_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    stars INT NOT NULL CHECK (stars BETWEEN 1 AND 5),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(job_id, rater_id, ratee_id) -- one rating per pair per job
);

-- ============================================================
-- LEADERBOARD VIEW
-- Derived from jobs and ratings, not a stored table
-- ============================================================
CREATE OR REPLACE VIEW public.leaderboard AS
SELECT
    p.id,
    p.sc_username,
    p.trust_score,
    p.trust_flag,
    COUNT(DISTINCT jm.job_id) FILTER (
        WHERE j.status = 'completed'
    ) AS jobs_completed,
    COALESCE(SUM(j.pay_auec) FILTER (
        WHERE j.status = 'completed'
    ), 0) AS total_earnings
FROM public.profiles p
LEFT JOIN public.job_members jm ON jm.user_id = p.id
LEFT JOIN public.jobs j ON j.id = jm.job_id
WHERE p.role = 'user'
GROUP BY p.id, p.sc_username, p.trust_score, p.trust_flag;

-- ============================================================
-- FUNCTIONS
-- ============================================================

-- Auto-create profile on user signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, sc_username, discord_handle, email)
    VALUES (
        NEW.id,
        NEW.raw_user_meta_data->>'sc_username',
        NEW.raw_user_meta_data->>'discord_handle',
        NEW.email
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Recalculate trust score and flag after a new rating
CREATE OR REPLACE FUNCTION public.update_trust_score()
RETURNS TRIGGER AS $$
DECLARE
    avg_score NUMERIC(3,2);
BEGIN
    SELECT AVG(stars) INTO avg_score
    FROM public.ratings
    WHERE ratee_id = NEW.ratee_id;

    UPDATE public.profiles SET
        trust_score = avg_score,
        trust_flag = CASE
            WHEN avg_score < 2.0 THEN 'low'
            WHEN avg_score > 4.0 THEN 'high'
            ELSE 'normal'
        END
    WHERE id = NEW.ratee_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_rating_inserted
    AFTER INSERT ON public.ratings
    FOR EACH ROW EXECUTE FUNCTION public.update_trust_score();

-- Update job status based on slots filled
CREATE OR REPLACE FUNCTION public.update_job_status()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE public.jobs SET
        slots_filled = (
            SELECT COUNT(*) FROM public.job_members WHERE job_id = NEW.job_id
        ),
        status = CASE
            WHEN (SELECT COUNT(*) FROM public.job_members WHERE job_id = NEW.job_id) = 0 THEN 'open'
            WHEN (SELECT COUNT(*) FROM public.job_members WHERE job_id = NEW.job_id) < slots_total THEN 'partial'
            ELSE 'full'
        END
    WHERE id = NEW.job_id AND status NOT IN ('in_progress', 'completed', 'failed');

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_job_member_change
    AFTER INSERT OR DELETE ON public.job_members
    FOR EACH ROW EXECUTE FUNCTION public.update_job_status();

-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.job_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ratings ENABLE ROW LEVEL SECURITY;

-- Profiles: users read all, edit only own
CREATE POLICY "profiles_read_all" ON public.profiles FOR SELECT USING (true);
CREATE POLICY "profiles_edit_own" ON public.profiles FOR UPDATE USING (auth.uid() = id);

-- Jobs: anyone reads, authenticated users insert, poster edits own
CREATE POLICY "jobs_read_all" ON public.jobs FOR SELECT USING (true);
CREATE POLICY "jobs_insert_auth" ON public.jobs FOR INSERT WITH CHECK (auth.uid() = poster_id);
CREATE POLICY "jobs_edit_own" ON public.jobs FOR UPDATE USING (auth.uid() = poster_id);

-- Job members: anyone reads, authenticated users insert own
CREATE POLICY "members_read_all" ON public.job_members FOR SELECT USING (true);
CREATE POLICY "members_insert_own" ON public.job_members FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "members_delete_own" ON public.job_members FOR DELETE USING (auth.uid() = user_id);

-- Ratings: anyone reads, authenticated users insert own ratings
CREATE POLICY "ratings_read_all" ON public.ratings FOR SELECT USING (true);
CREATE POLICY "ratings_insert_own" ON public.ratings FOR INSERT WITH CHECK (auth.uid() = rater_id);

-- ============================================================
-- SEED DATA (test entries)
-- ============================================================

INSERT INTO public.categories (name) VALUES
    ('Combat'),
    ('Hauling'),
    ('Mining'),
    ('Bounty Hunting'),
    ('Escort'),
    ('Salvage'),
    ('Exploration');
