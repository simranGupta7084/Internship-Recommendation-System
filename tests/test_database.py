import database


def teardown_function(_):
    database.internships_col.delete_many({})
    database.profiles_col.delete_many({})


def test_insert_and_get_internship():
    database.insert_internship({
        "title": "Backend Intern", "company": "Acme", "location": "Remote",
        "description": "Python and Flask work",
    })
    results = database.get_internships(query="Backend")
    assert len(results) == 1
    assert results[0]["company"] == "Acme"
    assert isinstance(results[0]["_id"], str)  # serialized, not a raw ObjectId


def test_duplicate_internship_is_ignored():
    job = {"title": "Dup Intern", "company": "Acme", "location": "Remote", "description": "x"}
    database.insert_internship(job)
    database.insert_internship(job)
    assert database.count_matching_internships(query="Dup Intern") == 1


def test_pagination_skip_and_limit():
    for i in range(5):
        database.insert_internship({
            "title": f"Intern {i}", "company": "Acme", "location": "Remote", "description": "x",
        })
    page1 = database.get_internships(limit=2, skip=0)
    page2 = database.get_internships(limit=2, skip=2)
    assert len(page1) == 2
    assert len(page2) == 2
    assert {d["title"] for d in page1}.isdisjoint({d["title"] for d in page2})


def test_upsert_and_get_profile():
    database.upsert_profile({"name": "alice", "skills": ["python"]})
    profile = database.get_profile("alice")
    assert profile["skills"] == ["python"]

    database.upsert_profile({"name": "alice", "skills": ["python", "sql"]})
    updated = database.get_profile("alice")
    assert updated["skills"] == ["python", "sql"]


def test_get_profile_missing_returns_none():
    assert database.get_profile("does_not_exist") is None
