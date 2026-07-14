import numpy as np
import matcher


def test_extract_skills_finds_known_terms():
    text = "I know Python, Flask, SQL and Git. Also some React."
    skills = matcher.extract_skills(text)
    assert set(skills) == {"python", "flask", "sql", "git", "react"}


def test_extract_skills_ignores_substrings():
    # "javascript" shouldn't match on partial word boundaries like "java" alone
    text = "I write javascript"
    skills = matcher.extract_skills(text)
    assert "javascript" in skills
    assert "java" not in skills


def test_recommend_rejects_empty_resume():
    result = matcher.recommend_for_resume("", [{"title": "x", "description": "y"}])
    assert "error" in result


def test_recommend_rejects_no_internships():
    result = matcher.recommend_for_resume("python developer", [])
    assert "error" in result


def test_recommend_ranks_by_similarity(monkeypatch):
    # Skip the real model download in tests: fake embeddings where index 0
    # (the resume) is closest to job 1, farthest from job 0.
    def fake_embed(texts):
        vectors = {
            "resume": [1.0, 0.0],
            "job_far": [0.0, 1.0],
            "job_close": [0.9, 0.1],
        }
        out = []
        for t in texts:
            if "resume text" in t:
                out.append(vectors["resume"])
            elif "far match" in t:
                out.append(vectors["job_far"])
            else:
                out.append(vectors["job_close"])
        return np.array(out)

    monkeypatch.setattr(matcher, "embed", fake_embed)

    internships = [
        {"id": "1", "title": "far match", "description": "unrelated field", "company": "A", "location": "X"},
        {"id": "2", "title": "close match", "description": "closely related role", "company": "B", "location": "Y"},
    ]
    result = matcher.recommend_for_resume("resume text here", internships, top_k=2)
    assert result["results"][0]["id"] == "2"  # closer match ranked first
