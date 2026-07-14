"""
Minimal API-key auth for write/admin endpoints.

Not OAuth/JWT — this is a small student project, not a multi-tenant SaaS.
An API key checked via a decorator is the appropriately-sized control here:
it stops an open internet route from writing to your database or burning
your external API quota, without pretending this needs session management.
"""
import os
from functools import wraps
from flask import request, jsonify

API_KEY = os.getenv("API_KEY")


def require_api_key(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not API_KEY:
            # Fail closed: if no key is configured, admin/write routes are disabled,
            # not silently open.
            return jsonify({"error": "Server misconfigured: API_KEY not set."}), 503
        provided = request.headers.get("X-API-Key")
        if provided != API_KEY:
            return jsonify({"error": "Missing or invalid X-API-Key header."}), 401
        return fn(*args, **kwargs)
    return wrapper
