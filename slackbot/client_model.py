"""
Client Model — persistent knowledge about each client.

Stores preferences, domain context, historical requests, and stakeholder info.
In production, this would map to Devin Knowledge Notes API.
For the prototype, we use local JSON files.
"""

import json
import os
from datetime import datetime
from typing import Optional

from config import CLIENT_MODELS_DIR


def _model_path(client_id: str) -> str:
    os.makedirs(CLIENT_MODELS_DIR, exist_ok=True)
    return os.path.join(CLIENT_MODELS_DIR, f"{client_id}.json")


def _default_model(client_id: str, client_name: str) -> dict:
    return {
        "client_id": client_id,
        "client_name": client_name,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "preferences": {
            "ui_style": [],
            "rejected_patterns": [],
            "preferred_patterns": [],
        },
        "domain_context": {
            "contract_tiers": [],
            "key_tables": [],
            "notes": [],
        },
        "stakeholders": [],
        "request_history": [],
    }


def load_model(client_id: str, client_name: str = "") -> dict:
    """Load a client model from disk, creating a default if it doesn't exist."""
    path = _model_path(client_id)
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    model = _default_model(client_id, client_name or client_id)
    save_model(client_id, model)
    return model


def save_model(client_id: str, model: dict) -> None:
    """Persist a client model to disk."""
    model["updated_at"] = datetime.utcnow().isoformat()
    path = _model_path(client_id)
    with open(path, "w") as f:
        json.dump(model, f, indent=2)


def add_preference(client_id: str, preference_type: str, value: str) -> None:
    """Add a UI/UX preference to the client model."""
    model = load_model(client_id)
    if preference_type in model["preferences"]:
        if value not in model["preferences"][preference_type]:
            model["preferences"][preference_type].append(value)
    save_model(client_id, model)


def add_domain_context(client_id: str, key: str, value: str) -> None:
    """Add domain-specific context (tables, tiers, etc.)."""
    model = load_model(client_id)
    if key in model["domain_context"]:
        if value not in model["domain_context"][key]:
            model["domain_context"][key].append(value)
    else:
        model["domain_context"][key] = [value]
    save_model(client_id, model)


def add_request(client_id: str, request_summary: dict) -> None:
    """Log a completed feature request to the client's history."""
    model = load_model(client_id)
    request_summary["timestamp"] = datetime.utcnow().isoformat()
    model["request_history"].append(request_summary)
    save_model(client_id, model)


def get_context_summary(client_id: str) -> str:
    """Generate a text summary of the client model for the LLM."""
    model = load_model(client_id)
    parts = [f"Client: {model['client_name']}"]

    prefs = model["preferences"]
    if prefs["preferred_patterns"]:
        parts.append(f"Preferred UI patterns: {', '.join(prefs['preferred_patterns'])}")
    if prefs["rejected_patterns"]:
        parts.append(f"Rejected UI patterns: {', '.join(prefs['rejected_patterns'])}")

    domain = model["domain_context"]
    if domain["contract_tiers"]:
        parts.append(f"Contract tiers: {', '.join(domain['contract_tiers'])}")
    if domain["notes"]:
        parts.append(f"Domain notes: {'; '.join(domain['notes'])}")

    history = model["request_history"]
    if history:
        recent = history[-5:]
        summaries = [f"- {r.get('title', 'Untitled')} ({r.get('status', 'unknown')})" for r in recent]
        parts.append(f"Recent requests:\n" + "\n".join(summaries))

    return "\n".join(parts)
