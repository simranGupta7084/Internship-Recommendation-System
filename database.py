"""
MongoDB access layer.
All credentials come from environment variables (.env) — never hardcoded.
"""
import os
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise RuntimeError(
        "MONGO_URI is not set. Copy .env.example to .env and fill in your "
        "MongoDB connection string before running the app."
    )

client = MongoClient(MONGO_URI)
db = client["internship_portal"]

internships_col = db["internships"]
profiles_col = db["profiles"]

# ------------------ Indexes ------------------
internships_col.create_index(
    [("title", 1), ("company", 1), ("location", 1)],
    unique=True,
)
internships_col.create_index("title")
internships_col.create_index("location")
profiles_col.create_index("name", unique=True)


# ------------------ Serialization helper ------------------
def _serialize(doc: dict) -> dict:
    """Convert a MongoDB document into a JSON-safe dict (str ObjectId, no raw datetimes issues)."""
    if doc is None:
        return None
    doc = dict(doc)
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


# ------------------ Internship helpers ------------------
def insert_internship(job: dict):
    """Insert internship, ignore duplicates (same title+company+location)."""
    try:
        internships_col.insert_one(job)
    except DuplicateKeyError:
        pass


def get_internships(query: str = None, location: str = None, limit: int = 50, skip: int = 0):
    """Fetch internships, optionally filtered by title/location substring. Always JSON-safe."""
    db_query = {}
    if query:
        db_query["title"] = {"$regex": query, "$options": "i"}
    if location:
        db_query["location"] = {"$regex": location, "$options": "i"}
    docs = internships_col.find(db_query).skip(skip).limit(limit)
    return [_serialize(d) for d in docs]


def count_matching_internships(query: str = None, location: str = None) -> int:
    db_query = {}
    if query:
        db_query["title"] = {"$regex": query, "$options": "i"}
    if location:
        db_query["location"] = {"$regex": location, "$options": "i"}
    return internships_col.count_documents(db_query)


def count_internships() -> int:
    return internships_col.estimated_document_count()


# ------------------ Profile helpers ------------------
def upsert_profile(profile: dict):
    """Create or update a user profile by name. profile must include 'name'."""
    name = profile.get("name")
    if not name:
        raise ValueError("Profile requires a 'name' field.")
    profiles_col.update_one({"name": name}, {"$set": profile}, upsert=True)
    return get_profile(name)


def get_profile(name: str):
    doc = profiles_col.find_one({"name": name})
    return _serialize(doc)


def get_profiles():
    return [_serialize(d) for d in profiles_col.find()]
