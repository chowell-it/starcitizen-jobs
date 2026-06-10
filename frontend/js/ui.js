/**
 * Shared UI helpers
 * Used across all pages: nav injection, toast notifications, badge rendering.
 */

import { Auth } from "./api.js";

/** Inject nav into any page that has <nav id="main-nav"> */
export function renderNav() {
    const nav = document.getElementById("main-nav");
    if (!nav) return;

    const user = Auth.currentUser();
    const isAdmin = user?.role === "admin";

    nav.innerHTML = `
        <a class="nav-logo" href="/index.html">UEE <span>Operations</span></a>
        <ul class="nav-links">
            <li><a href="/index.html">Board</a></li>
            <li><a href="/pages/leaderboard.html">Leaderboard</a></li>
            ${user ? `<li><a href="/pages/submit.html">Post Job</a></li>` : ""}
            ${user ? `<li><a href="/pages/profile.html?id=${user.id}">Profile</a></li>` : ""}
            ${isAdmin ? `<li><a href="/pages/admin.html">Admin</a></li>` : ""}
            ${user
                ? `<li><button class="btn btn-outline" id="logout-btn">Logout</button></li>`
                : `<li><a href="/pages/login.html">Login</a></li>`
            }
        </ul>
    `;

    document.getElementById("logout-btn")?.addEventListener("click", Auth.logout);

    // Highlight active link
    document.querySelectorAll(".nav-links a").forEach(a => {
        if (a.href === window.location.href) a.classList.add("active");
    });
}

/** Show a toast notification at bottom-right */
export function toast(message, type = "info") {
    let container = document.getElementById("toast-container");
    if (!container) {
        container = document.createElement("div");
        container.id = "toast-container";
        document.body.appendChild(container);
    }

    const el = document.createElement("div");
    el.className = `toast${type === "error" ? " error" : ""}`;
    el.textContent = message;
    container.appendChild(el);

    // Auto-remove after 3s
    setTimeout(() => el.remove(), 3000);
}

/** Render a status badge */
export function statusBadge(status) {
    return `<span class="badge badge-status-${status}">${status.replace("_", " ")}</span>`;
}

/** Render a difficulty badge */
export function diffBadge(diff) {
    return `<span class="badge badge-diff-${diff.toLowerCase()}">${diff}</span>`;
}

/** Render a trust flag badge (only low/high shown) */
export function trustBadge(flag) {
    if (flag === "normal") return "";
    return `<span class="badge badge-trust-${flag}">${flag} trust</span>`;
}

/** Format aUEC number with commas */
export function formatAUEC(n) {
    return Number(n).toLocaleString() + " aUEC";
}

/** Open job detail in new tab or same tab based on user preference */
export function openJob(jobId) {
    const user = Auth.currentUser();
    const newTab = user?.job_tab_preference !== false; // default true
    const url = `/pages/job.html?id=${jobId}`;
    if (newTab) window.open(url, "_blank");
    else window.location.href = url;
}
