import requests

BASE = "http://127.0.0.1:5000"

print("== health ==")
print(requests.get(f"{BASE}/health").json())

print("== refresh (populates DB from external APIs) ==")
print(requests.post(f"{BASE}/admin/refresh", json={"query": "internship", "location": "India", "top_k": 20}).json())

print("== save profile ==")
profile = {
    "name": "test_user",
    "skills": ["python", "flask", "sql", "git"],
    "resume_text": "I know Python, Flask, SQL and Git. Built REST APIs and worked with MongoDB.",
    "preferred_location": "India",
}
print(requests.post(f"{BASE}/profile", json=profile).json())

print("== recommend from saved profile ==")
resp = requests.post(f"{BASE}/recommend", json={"profile_name": "test_user", "top_k": 3})
print("Status:", resp.status_code)
print(resp.json())
