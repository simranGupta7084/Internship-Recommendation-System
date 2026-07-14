import os
import sys

# Must happen before any test module imports `database`, since database.py
# opens its Mongo connection at import time. mongomock swaps in an in-memory
# Mongo so tests never touch a real database or network.
import mongomock
import pymongo
pymongo.MongoClient = mongomock.MongoClient

os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017/")
os.environ.setdefault("API_KEY", "test-key")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
