"""
Devin API Integration — for production use.

This module wraps the Devin v3 API for:
1. Creating prototype sessions (parallel variant generation)
2. Managing playbooks
3. Syncing client models to Knowledge Notes

For the prototype demo, the prototype_generator.py module handles
variant generation locally. This module is the production upgrade path.
"""

import time
from typing import Optional

import requests

import config

BASE_URL = "https://api.devin.ai/v3/organizations"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {config.DEVIN_API_KEY}",
        "Content-Type": "application/json",
    }


def is_configured() -> bool:
    """Check if the Devin API is configured."""
    return bool(config.DEVIN_API_KEY)


def create_prototype_session(
    prompt: str,
    playbook_id: Optional[str] = None,
) -> Optional[dict]:
    """
    Create a Devin session for prototype generation.

    Returns the session info dict with devin_id, or None on failure.
    """
    if not is_configured():
        return None

    payload = {"prompt": prompt}
    if playbook_id:
        payload["playbook_id"] = playbook_id

    resp = requests.post(
        f"{BASE_URL}/sessions",
        headers=_headers(),
        json=payload,
    )
    if resp.status_code in (200, 201):
        return resp.json()

    print(f"Devin session creation failed: {resp.status_code} {resp.text}")
    return None


def poll_session(devin_id: str, timeout_seconds: int = 600) -> Optional[dict]:
    """
    Poll a Devin session until it completes or times out.
    Returns the final session state including structured_output.
    """
    if not is_configured():
        return None

    start = time.time()
    while time.time() - start < timeout_seconds:
        resp = requests.get(
            f"{BASE_URL}/sessions/{devin_id}",
            headers=_headers(),
        )
        if resp.status_code == 200:
            data = resp.json()
            status = data.get("status", "")
            if status in ("completed", "stopped", "failed"):
                return data
        time.sleep(15)

    return None


def create_parallel_prototypes(
    base_prompt: str,
    variant_descriptions: list[str],
    playbook_id: Optional[str] = None,
) -> list[dict]:
    """
    Create 3 parallel Devin sessions, one per variant.
    Returns a list of session results with structured output.
    """
    sessions = []
    for desc in variant_descriptions:
        prompt = f"{base_prompt}\n\nAPPROACH: {desc}"
        session = create_prototype_session(prompt, playbook_id)
        if session:
            sessions.append(session)

    # Poll all sessions
    results = []
    for session in sessions:
        result = poll_session(session["devin_id"])
        if result:
            results.append(result)

    return results


def sync_knowledge_note(
    client_id: str,
    content: str,
    note_id: Optional[str] = None,
) -> Optional[str]:
    """
    Create or update a Knowledge Note for a client model.
    Returns the note_id.
    """
    if not is_configured():
        return None

    if note_id:
        resp = requests.put(
            f"{BASE_URL}/knowledge/notes/{note_id}",
            headers=_headers(),
            json={
                "title": f"Client Model: {client_id}",
                "content": content,
            },
        )
    else:
        resp = requests.post(
            f"{BASE_URL}/knowledge/notes",
            headers=_headers(),
            json={
                "title": f"Client Model: {client_id}",
                "content": content,
                "trigger_description": f"Working on features for client {client_id}",
            },
        )

    if resp.status_code in (200, 201):
        return resp.json().get("note_id")

    print(f"Knowledge note sync failed: {resp.status_code} {resp.text}")
    return None
