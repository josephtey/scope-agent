"""
Client Model — persistent knowledge about each client.

Stores preferences, domain context, historical requests, and stakeholder info.
Uses local JSON files as the primary store, and optionally syncs to
Devin Knowledge Notes API so that Devin sessions automatically recall
client context when generating prototypes.
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


# --- Devin Knowledge Notes Sync ---

# Cache of knowledge note IDs per client (client_id -> note_id)
_knowledge_note_ids: dict[str, str] = {}


def sync_to_knowledge_notes(client_id: str) -> Optional[str]:
    """
    Sync the client model to a Devin Knowledge Note.

    This ensures Devin sessions automatically recall client context
    when generating prototypes for this client.

    Returns the knowledge note ID or None if sync is unavailable.
    """
    try:
        import devin_integration
    except ImportError:
        return None

    if not devin_integration.is_configured():
        return None

    model = load_model(client_id)
    content = _format_knowledge_note(model)
    existing_note_id = _knowledge_note_ids.get(client_id) or model.get("knowledge_note_id")

    note_id = devin_integration.sync_knowledge_note(
        client_id=client_id,
        content=content,
        note_id=existing_note_id,
        trigger_description=f"Working on features for client {model.get('client_name', client_id)}",
    )

    if note_id:
        _knowledge_note_ids[client_id] = note_id
        # Persist the note ID in the local model too
        model["knowledge_note_id"] = note_id
        save_model(client_id, model)

    return note_id


def _format_knowledge_note(model: dict) -> str:
    """Format a client model as a Knowledge Note body."""
    parts = [
        f"# Client Model: {model.get('client_name', model.get('client_id', 'Unknown'))}",
        "",
    ]

    prefs = model.get("preferences", {})
    if any(prefs.values()):
        parts.append("## Preferences")
        for key, values in prefs.items():
            if values:
                parts.append(f"- **{key}**: {', '.join(values)}")
        parts.append("")

    domain = model.get("domain_context", {})
    if any(domain.values()):
        parts.append("## Domain Context")
        for key, values in domain.items():
            if values:
                parts.append(f"- **{key}**: {', '.join(values) if isinstance(values, list) else values}")
        parts.append("")

    history = model.get("request_history", [])
    if history:
        parts.append("## Request History")
        for req in history[-10:]:
            title = req.get("title", "Untitled")
            status = req.get("status", "unknown")
            parts.append(f"- {title} ({status})")
        parts.append("")

    return "\n".join(parts)
