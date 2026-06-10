/**
 * API client
 * All backend calls go through here. Token stored in localStorage.
 */

const API_BASE = "https://starcitizen-jobs-production.up.railway.app/api";

/** Attach auth header if token exists */
function authHeaders() {
    const token = localStorage.getItem("sc_token");
    return token ? { "Authorization": `Bearer ${token}`, "Content-Type": "application/json" }
                 : { "Content-Type": "application/json" };
}

/** Generic fetch wrapper */
async function apiFetch(path, options = {}) {
    const res = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers: { ...authHeaders(), ...options.headers },
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || "Request failed");
    }
    return res.json();
}

// ── Auth ─────────────────────────────────────────────────────
export const Auth = {
    /** Register new account */
    register: (data) => apiFetch("/auth/register", { method: "POST", body: JSON.stringify(data) }),

    /** Login and store token */
    login: async (sc_username, password) => {
        const data = await apiFetch("/auth/login", {
            method: "POST",
            body: JSON.stringify({ sc_username, password }),
        });
        localStorage.setItem("sc_token", data.access_token);
        localStorage.setItem("sc_user", JSON.stringify(data.user));
        return data;
    },

    /** Clear session */
    logout: () => {
        localStorage.removeItem("sc_token");
        localStorage.removeItem("sc_user");
        window.location.href = "/pages/login.html";
    },

    /** Get stored user object */
    currentUser: () => JSON.parse(localStorage.getItem("sc_user") || "null"),

    /** Redirect to login if not authenticated */
    requireAuth: () => {
        if (!localStorage.getItem("sc_token")) window.location.href = "/pages/login.html";
    },
};

// ── Jobs ─────────────────────────────────────────────────────
export const Jobs = {
    /** List jobs with optional filter params object */
    list: (params = {}) => {
        const qs = new URLSearchParams(params).toString();
        return apiFetch(`/jobs${qs ? "?" + qs : ""}`);
    },

    /** Get single job detail */
    get: (id) => apiFetch(`/jobs/${id}`),

    /** Create a new job posting */
    create: (data) => apiFetch("/jobs", { method: "POST", body: JSON.stringify(data) }),

    /** Accept (join) a job */
    accept: (id) => apiFetch(`/jobs/${id}/accept`, { method: "POST" }),

    /** Update job status (poster only) */
    updateStatus: (id, status, failure_reason = null) =>
        apiFetch(`/jobs/${id}/status`, { method: "PATCH", body: JSON.stringify({ status, failure_reason }) }),

    /** Submit a rating for a user on a completed job */
    rate: (job_id, ratee_id, stars) =>
        apiFetch(`/jobs/${job_id}/rate`, { method: "POST", body: JSON.stringify({ ratee_id, stars }) }),
};

// ── Users ─────────────────────────────────────────────────────
export const Users = {
    getProfile: (id) => apiFetch(`/users/${id}`),
    updateSettings: (data) => apiFetch("/users/me/settings", { method: "PATCH", body: JSON.stringify(data) }),
};

// ── Leaderboard ───────────────────────────────────────────────
export const Leaderboard = {
    get: (sort_by = "jobs_completed") => apiFetch(`/leaderboard?sort_by=${sort_by}`),
};

// ── Admin ─────────────────────────────────────────────────────
export const Admin = {
    pendingJobs: () => apiFetch("/admin/jobs/pending"),
    approveJob: (id, approved) => apiFetch(`/admin/jobs/${id}/approve`, { method: "PATCH", body: JSON.stringify({ approved }) }),
    forceJobStatus: (id, status, failure_reason) => apiFetch(`/admin/jobs/${id}/status`, { method: "PATCH", body: JSON.stringify({ status, failure_reason }) }),
    deleteJob: (id) => apiFetch(`/admin/jobs/${id}`, { method: "DELETE" }),
    listUsers: () => apiFetch("/admin/users"),
    updateRole: (user_id, role) => apiFetch(`/admin/users/${user_id}/role`, { method: "PATCH", body: JSON.stringify({ role }) }),
    deleteUser: (id) => apiFetch(`/admin/users/${id}`, { method: "DELETE" }),
};
