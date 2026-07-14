"""
Semantic matching between a resume/profile and internship listings.

Uses sentence-transformers embeddings + cosine similarity instead of TF-IDF.
TF-IDF only catches exact/overlapping vocabulary — "built REST APIs" and
"developed backend services" score as unrelated. Embeddings capture that
they mean roughly the same thing, which is the actual point of a
recommendation system.
"""
import re
import numpy as np

_MODEL = None

SKILL_LIST = [
    "python", "flask", "fastapi", "django", "sql", "mysql", "postgresql",
    "rest", "api", "git", "docker", "linux",
    "html", "css", "javascript", "react", "tailwind",
    "java", "spring", "spring boot",
    "excel", "pandas", "numpy", "scikit-learn", "machine learning", "ml",
]


def get_model():
    """Lazy-load the embedding model once per process (it's ~80MB, don't reload per request).

    Imported here rather than at module level so anything that only needs
    extract_skills() (like tests, or the skill-gap endpoint) doesn't require
    sentence-transformers/torch to be installed at all.
    """
    global _MODEL
    if _MODEL is None:
        from sentence_transformers import SentenceTransformer
        _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return _MODEL


def extract_skills(text: str) -> list:
    found = []
    low = (text or "").lower()
    for skill in SKILL_LIST:
        if re.search(r"\b" + re.escape(skill) + r"\b", low):
            found.append(skill)
    return sorted(set(found))


def embed(texts: list) -> np.ndarray:
    model = get_model()
    return model.encode(texts, normalize_embeddings=True)


def cosine_sim_matrix(query_vec: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    # vectors are already normalized, so cosine similarity is just the dot product
    return matrix @ query_vec


def recommend_for_resume(resume_text: str, internships: list, top_k: int = 3) -> dict:
    if not resume_text.strip():
        return {"error": "Empty resume text."}
    if not internships:
        return {"error": "No internships available to match against."}

    job_texts = [f"{j.get('title','')}. {j.get('description','')}" for j in internships]
    all_vecs = embed([resume_text] + job_texts)
    resume_vec, job_vecs = all_vecs[0], all_vecs[1:]

    sims = cosine_sim_matrix(resume_vec, job_vecs)
    rank_idx = np.argsort(sims)[::-1][: min(top_k, len(internships))]

    resume_skills = extract_skills(resume_text)
    results = []
    for i in rank_idx:
        job = internships[i]
        job_skills = extract_skills(job_texts[i])
        missing = sorted(set(job_skills) - set(resume_skills))
        results.append({
            "id": job.get("id") or job.get("_id"),
            "title": job.get("title"),
            "location": job.get("location", ""),
            "description": job.get("description"),
            "score": round(float(sims[i]), 4),
            "skills_required": job_skills,
            "resume_skills": resume_skills,
            "missing_skills": missing,
            "link": job.get("link", "#"),
            "company": job.get("company", "N/A"),
            "salary": job.get("salary", "Not disclosed"),
            "source": job.get("source", "unknown"),
        })

    return {"query_resume": resume_text, "top_k": top_k, "results": results}
