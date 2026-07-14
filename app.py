import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from database import (
    insert_internship, get_internships, count_internships, count_matching_internships,
    upsert_profile, get_profile,
)
from data_loader import load_internships_combined
from matcher import recommend_for_resume, extract_skills
from auth import require_api_key

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)
limiter = Limiter(get_remote_address, app=app, default_limits=["120 per hour"])


# ---------------- Refresh (decoupled from request path) ----------------
def refresh_internships(query="internship", location="India", top_k=30):
    """Pull fresh listings from external APIs into MongoDB.

    Deliberately NOT called on every /recommend request — that made every
    recommendation depend on three synchronous external HTTP calls, which is
    slow and burns free-tier rate limits. Call this from a scheduled job
    (cron / APScheduler) or the admin endpoint below instead.
    """
    jobs = load_internships_combined(query, location, top_k=top_k)
    for job in jobs:
        insert_internship(job)
    log.info("Refreshed %d internships (query=%r, location=%r)", len(jobs), query, location)
    return len(jobs)


# ---------------- Routes ----------------
@app.get("/health")
def health():
    return jsonify({"status": "ok", "internships_cached": count_internships()})


@app.get("/internships")
def list_internships():
    query = request.args.get("query", "")
    location = request.args.get("location", "")
    page = max(1, int(request.args.get("page", 1)))
    per_page = min(int(request.args.get("per_page", 20)), 100)

    items = get_internships(query=query, location=location, limit=per_page, skip=(page - 1) * per_page)
    total = count_matching_internships(query=query, location=location)
    return jsonify({
        "count": len(items),
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page if per_page else 0,
        "items": items,
    })


@app.post("/admin/refresh")
@limiter.limit("5 per hour")
@require_api_key
def admin_refresh():
    data = request.get_json(force=True, silent=True) or {}
    query = data.get("query", "internship")
    location = data.get("location", "India")
    top_k = min(int(data.get("top_k", 30)), 100)
    n = refresh_internships(query, location, top_k)
    return jsonify({"refreshed": n})


@app.post("/profile")
@require_api_key
def save_profile():
    data = request.get_json(force=True, silent=True) or {}
    if not data.get("name"):
        return jsonify({"error": "Profile requires a 'name' field."}), 400
    profile = upsert_profile(data)
    return jsonify(profile)


@app.get("/profile/<name>")
def load_profile(name):
    profile = get_profile(name)
    if not profile:
        return jsonify({"error": "Profile not found."}), 404
    return jsonify(profile)


@app.post("/recommend")
@limiter.limit("30 per hour")
def recommend_endpoint():
    """Recommend internships from raw resume text or a saved profile.
    Matches against whatever is currently cached in MongoDB — call
    POST /admin/refresh separately (with an API key) to populate that cache.
    """
    data = request.get_json(force=True, silent=True) or {}
    resume_text = (data.get("resume") or "").strip()

    if not resume_text and data.get("profile_name"):
        profile = get_profile(data["profile_name"])
        if profile:
            resume_text = profile.get("resume_text", "") or " ".join(profile.get("skills", []))

    if not resume_text:
        skills = data.get("skills")
        if isinstance(skills, list) and skills:
            resume_text = " ".join(map(str, skills))

    top_k = max(1, min(int(data.get("top_k", 3)), 10))

    internships = get_internships(limit=200)
    if not internships:
        return jsonify({"error": "No internships cached yet. Call POST /admin/refresh first."}), 409

    payload = recommend_for_resume(resume_text, internships, top_k)
    if "error" in payload:
        return jsonify(payload), 400
    return jsonify(payload)


@app.get("/skill-gap/<name>")
def skill_gap(name):
    """Aggregate which skills show up most often in cached internships that the
    named profile doesn't have — a concrete 'what should I learn next' answer,
    which is what actually differentiates a recommendation system from search."""
    profile = get_profile(name)
    if not profile:
        return jsonify({"error": "Profile not found."}), 404

    have = set(extract_skills(profile.get("resume_text", "") or " ".join(profile.get("skills", []))))
    internships = get_internships(limit=200)

    gap_counts = {}
    for job in internships:
        job_text = f"{job.get('title','')} {job.get('description','')}"
        for skill in extract_skills(job_text):
            if skill not in have:
                gap_counts[skill] = gap_counts.get(skill, 0) + 1

    ranked = sorted(gap_counts.items(), key=lambda kv: kv[1], reverse=True)
    return jsonify({
        "name": name,
        "known_skills": sorted(have),
        "recommended_to_learn": [{"skill": s, "demand": c} for s, c in ranked[:10]],
    })


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=False)
