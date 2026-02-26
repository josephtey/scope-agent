"""
Devin API Integration — production prototype generation.

Uses the Devin v3 API (Service Users) to:
1. Create prototype sessions that modify the client project repo
2. Poll sessions and extract structured output (screenshot URLs, descriptions)
3. Create and manage playbooks for prototype generation
4. Sync client models to Knowledge Notes

API Reference: https://docs.devin.ai/api-reference/overview
"""

import json
import time
import concurrent.futures
from typing import Optional

import requests

import config

# v3 Organization API — org_id is resolved from the cog_ credential
BASE_URL = "https://api.devin.ai/v3/organizations"

# Structured output schema for prototype sessions
PROTOTYPE_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "variant_name": {"type": "string", "description": "Short name for this variant approach"},
        "description": {"type": "string", "description": "One-sentence description of the UI approach"},
        "files_changed": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of files modified in the prototype",
        },
        "screenshot_url": {
            "type": "string",
            "description": "URL of a screenshot of the prototype (if available)",
        },
        "preview_url": {
            "type": "string",
            "description": "URL where the prototype can be previewed live (if deployed)",
        },
    },
    "required": ["variant_name", "description", "files_changed"],
}

# The playbook content that instructs Devin how to generate a prototype variant
PROTOTYPE_PLAYBOOK_BODY = """# Prototype Variant Generator

## Goal
You are generating a UI prototype variant for a B2B SaaS dashboard app.
The client has requested a specific feature change, and you must implement ONE approach to it.

## Procedure
1. Clone the repository specified in the prompt
2. Run `npm install` to set up dependencies
3. Read the existing code to understand the component structure
4. Implement the requested feature change following the specified approach
5. Run `npm run build` to verify the code compiles
6. Take a screenshot of the result if possible
7. Create a PR with your changes (do NOT merge it)

## Specifications
- Make minimal, focused changes — only modify what's needed for this variant
- Follow the existing code style and conventions
- Keep the same overall layout and color scheme
- The change should be visually distinct from the current state
- Update structured output with your results in this format:

```json
{
  "variant_name": "Short name (e.g., 'Dropdown Filter')",
  "description": "One sentence describing the approach",
  "files_changed": ["src/components/Example.jsx"],
  "screenshot_url": "URL if you took a screenshot",
  "preview_url": "URL if you deployed a preview"
}
```

## Advice
- Focus on the UI change only — don't refactor unrelated code
- If the prompt says "Option A", "Option B", etc., implement ONLY that option
- Keep it simple and clean — this is a prototype, not production code
"""


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {config.DEVIN_API_KEY}",
        "Content-Type": "application/json",
    }


def is_configured() -> bool:
    """Check if the Devin API is configured with a valid key."""
    return bool(config.DEVIN_API_KEY)


def test_connection() -> dict:
    """Test the API connection. Returns status info or error details."""
    if not is_configured():
        return {"ok": False, "error": "DEVIN_API_KEY not set"}

    try:
        resp = requests.get(
            f"{BASE_URL}/sessions",
            headers=_headers(),
            params={"limit": 1},
            timeout=10,
        )
        if resp.status_code == 200:
            return {"ok": True, "status_code": 200}
        return {
            "ok": False,
            "status_code": resp.status_code,
            "error": resp.text[:200],
        }
    except requests.RequestException as e:
        return {"ok": False, "error": str(e)}


# --- Playbook Management ---


def create_playbook(title: str, body: str) -> Optional[str]:
    """
    Create a Devin playbook via the v1 API.
    Returns the playbook_id or None on failure.

    Note: Playbook creation uses v1 API as v3 playbook endpoints
    may require different permissions.
    """
    if not is_configured():
        return None

    resp = requests.post(
        "https://api.devin.ai/v1/playbooks",
        headers=_headers(),
        json={"title": title, "body": body},
        timeout=30,
    )
    if resp.status_code in (200, 201):
        data = resp.json()
        return data.get("playbook_id")

    print(f"Playbook creation failed: {resp.status_code} {resp.text[:200]}")
    return None


def ensure_prototype_playbook() -> Optional[str]:
    """
    Get or create the prototype generation playbook.
    Returns the playbook_id.
    """
    # If already configured, use it
    if config.PROTOTYPE_PLAYBOOK_ID:
        return config.PROTOTYPE_PLAYBOOK_ID

    # Try to create one
    playbook_id = create_playbook(
        title="Scope Agent — Prototype Variant Generator",
        body=PROTOTYPE_PLAYBOOK_BODY,
    )
    if playbook_id:
        print(f"Created prototype playbook: {playbook_id}")
    return playbook_id


# --- Session Management ---


def create_session(
    prompt: str,
    playbook_id: Optional[str] = None,
    repos: Optional[list[str]] = None,
    structured_output_schema: Optional[dict] = None,
    tags: Optional[list[str]] = None,
    title: Optional[str] = None,
) -> Optional[dict]:
    """
    Create a Devin session via v3 API.

    Returns the session response dict with session_id, url, status, etc.
    Returns None on failure.
    """
    if not is_configured():
        return None

    payload: dict = {"prompt": prompt}
    if playbook_id:
        payload["playbook_id"] = playbook_id
    if repos:
        payload["repos"] = repos
    if structured_output_schema:
        payload["structured_output_schema"] = structured_output_schema
    if tags:
        payload["tags"] = tags
    if title:
        payload["title"] = title

    try:
        resp = requests.post(
            f"{BASE_URL}/sessions",
            headers=_headers(),
            json=payload,
            timeout=30,
        )
        if resp.status_code in (200, 201):
            return resp.json()

        print(f"Devin session creation failed: {resp.status_code} {resp.text[:200]}")
        return None
    except requests.RequestException as e:
        print(f"Devin session creation error: {e}")
        return None


def get_session(session_id: str) -> Optional[dict]:
    """Get the current state of a Devin session."""
    if not is_configured():
        return None

    try:
        resp = requests.get(
            f"{BASE_URL}/sessions/{session_id}",
            headers=_headers(),
            timeout=15,
        )
        if resp.status_code == 200:
            return resp.json()
        return None
    except requests.RequestException:
        return None


def is_session_done(session: dict) -> bool:
    """
    Check if a session has finished (successfully or with error).

    v3 status values: new, claimed, running, exit, error, suspended, resuming
    status_detail when running: working, waiting_for_user, waiting_for_approval, finished
    """
    status = session.get("status", "")
    status_detail = session.get("status_detail", "")

    # Terminal states
    if status in ("exit", "error", "suspended"):
        return True

    # Running but finished
    if status == "running" and status_detail == "finished":
        return True

    return False


def is_session_successful(session: dict) -> bool:
    """Check if a session completed successfully."""
    status = session.get("status", "")
    status_detail = session.get("status_detail", "")

    if status == "running" and status_detail == "finished":
        return True
    if status == "exit":
        return True

    return False


def poll_session(
    session_id: str,
    timeout_seconds: Optional[int] = None,
    poll_interval: Optional[int] = None,
    on_progress: Optional[callable] = None,
) -> Optional[dict]:
    """
    Poll a Devin session until it completes or times out.

    Args:
        session_id: The session ID to poll
        timeout_seconds: Max time to wait (default from config)
        poll_interval: Seconds between polls (default from config)
        on_progress: Optional callback(session_dict) called on each poll

    Returns the final session state or None on timeout.
    """
    if not is_configured():
        return None

    timeout = timeout_seconds or config.DEVIN_SESSION_TIMEOUT
    interval = poll_interval or config.DEVIN_POLL_INTERVAL
    start = time.time()

    while time.time() - start < timeout:
        session = get_session(session_id)
        if session is None:
            time.sleep(interval)
            continue

        if on_progress:
            on_progress(session)

        if is_session_done(session):
            return session

        time.sleep(interval)

    print(f"Session {session_id} timed out after {timeout}s")
    return None


def send_message(session_id: str, message: str) -> bool:
    """Send a message to an active Devin session."""
    if not is_configured():
        return False

    try:
        resp = requests.post(
            f"{BASE_URL}/sessions/{session_id}/message",
            headers=_headers(),
            json={"message": message},
            timeout=15,
        )
        return resp.status_code in (200, 201)
    except requests.RequestException:
        return False


# --- Prototype Generation ---


def create_prototype_sessions(
    feature_description: str,
    variant_approaches: list[dict],
    client_context: str = "",
) -> list[dict]:
    """
    Create parallel Devin sessions to generate prototype variants.

    Args:
        feature_description: What the client wants (from scoping conversation)
        variant_approaches: List of dicts with 'name' and 'approach' keys
        client_context: Summary of client preferences from the client model

    Returns list of created session dicts (with session_id, url, etc.)
    """
    playbook_id = ensure_prototype_playbook()
    repo = config.CLIENT_PROJECT_REPO
    sessions = []

    for i, variant in enumerate(variant_approaches):
        prompt = _build_variant_prompt(
            feature_description=feature_description,
            variant_name=variant["name"],
            approach=variant["approach"],
            client_context=client_context,
            repo=repo,
        )

        session = create_session(
            prompt=prompt,
            playbook_id=playbook_id,
            repos=[repo],
            structured_output_schema=PROTOTYPE_OUTPUT_SCHEMA,
            tags=["scope-agent", "prototype", f"variant-{i+1}"],
            title=f"Prototype: {variant['name']}",
        )

        if session:
            sessions.append({
                **session,
                "variant_name": variant["name"],
                "variant_approach": variant["approach"],
            })
            print(f"Created session for '{variant['name']}': {session.get('url', 'no url')}")
        else:
            print(f"Failed to create session for variant: {variant['name']}")

    return sessions


def poll_prototype_sessions(
    sessions: list[dict],
    on_variant_complete: Optional[callable] = None,
) -> list[dict]:
    """
    Poll all prototype sessions until they complete.

    Args:
        sessions: List of session dicts from create_prototype_sessions
        on_variant_complete: Optional callback(variant_result) for each completed variant

    Returns list of result dicts with session data + structured output.
    """
    results = []

    def _poll_one(session_info):
        session_id = session_info["session_id"]
        final = poll_session(session_id)
        if final:
            result = {
                "session_id": session_id,
                "variant_name": session_info.get("variant_name", "Unknown"),
                "variant_approach": session_info.get("variant_approach", ""),
                "url": final.get("url", ""),
                "status": final.get("status", "unknown"),
                "status_detail": final.get("status_detail", ""),
                "structured_output": final.get("structured_output"),
                "pull_requests": final.get("pull_requests", []),
                "success": is_session_successful(final),
            }
            if on_variant_complete:
                on_variant_complete(result)
            return result
        return {
            "session_id": session_id,
            "variant_name": session_info.get("variant_name", "Unknown"),
            "success": False,
            "status": "timeout",
        }

    # Poll sessions in parallel using threads
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(_poll_one, s): s for s in sessions}
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    return results


def _build_variant_prompt(
    feature_description: str,
    variant_name: str,
    approach: str,
    client_context: str,
    repo: str,
) -> str:
    """Build the prompt for a single prototype variant session."""
    prompt = f"""Generate a prototype variant for a client's feature request.

## Repository
{repo}

## Feature Request
{feature_description}

## Your Approach: {variant_name}
{approach}

## Client Preferences
{client_context if client_context else "No specific preferences noted yet."}

## Instructions
1. Clone the repo and understand the current dashboard structure
2. Implement the feature using the approach described above
3. Make sure `npm run build` passes
4. Create a PR with your changes (title: "Prototype: {variant_name}")
5. Update the structured output with your results

Keep changes minimal and focused on this one feature variant.
"""
    return prompt


# --- Knowledge Notes ---


def sync_knowledge_note(
    client_id: str,
    content: str,
    note_id: Optional[str] = None,
    trigger_description: Optional[str] = None,
) -> Optional[str]:
    """
    Create or update a Knowledge Note for a client model.
    Returns the note_id or None on failure.
    """
    if not is_configured():
        return None

    try:
        if note_id:
            resp = requests.patch(
                f"{BASE_URL}/knowledge/{note_id}",
                headers=_headers(),
                json={
                    "title": f"Client Model: {client_id}",
                    "body": content,
                },
                timeout=15,
            )
        else:
            payload = {
                "title": f"Client Model: {client_id}",
                "body": content,
            }
            if trigger_description:
                payload["trigger_description"] = trigger_description
            resp = requests.post(
                f"{BASE_URL}/knowledge",
                headers=_headers(),
                json=payload,
                timeout=15,
            )

        if resp.status_code in (200, 201):
            data = resp.json()
            return data.get("knowledge_id") or data.get("note_id")

        print(f"Knowledge note sync failed: {resp.status_code} {resp.text[:200]}")
        return None
    except requests.RequestException as e:
        print(f"Knowledge note sync error: {e}")
        return None
