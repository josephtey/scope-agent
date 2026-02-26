"""
Prototype Generator — creates visual variants of dashboard features using Devin API.

Spins up 3 parallel Devin sessions via the API, each implementing a different variant
of the requested feature on the real client project repo (josephtey/sample-client-project).
Each session modifies the code, runs the app, takes a browser screenshot, and returns
the screenshot URL.

The scoping agent decides when to prototype and provides the feature description.
This module generates 3 variant approaches and delegates to Devin.
"""

import json
from typing import Optional

import devin_integration
from client_model import get_context_summary


# --- Variant Approach Generation ---

def generate_variant_approaches(feature_description: str) -> list[dict]:
    """
    Generate 3 different UI approaches for a feature request.

    In the future this could use an LLM to suggest approaches dynamically.
    For now, we generate 3 standard UI pattern variations.
    """
    # Try to use OpenAI to generate dynamic approaches
    try:
        from openai import OpenAI
        import config
        if config.OPENAI_API_KEY:
            client = OpenAI(api_key=config.OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You generate 3 different UI approaches for implementing a feature request "
                            "on a B2B SaaS dashboard. Each approach should be a genuinely different "
                            "UI pattern (e.g., dropdown vs tabs vs inline). Return valid JSON only — "
                            'an array of 3 objects each with "name" (short label) and "approach" '
                            "(1-2 sentence description of the UI implementation)."
                        ),
                    },
                    {"role": "user", "content": feature_description},
                ],
                temperature=0.8,
                max_tokens=500,
            )
            raw = response.choices[0].message.content or ""
            # Strip markdown code block wrappers if present
            raw = raw.strip()
            if raw.startswith("```"):
                # Remove opening ```json or ``` line
                first_newline = raw.index("\n")
                raw = raw[first_newline + 1:]
                # Remove closing ```
                if raw.endswith("```"):
                    raw = raw[:-3].strip()
            approaches = json.loads(raw)
            if isinstance(approaches, list) and len(approaches) >= 3:
                return approaches[:3]
    except Exception as e:
        print(f"LLM variant generation failed ({e}), using defaults")

    # Default: 3 standard UI approaches
    return [
        {
            "name": "Option A — Dropdown Filter",
            "approach": (
                "Add a dropdown/select element at the top of the relevant table or section. "
                "Users select an option to filter the data. Clean, minimal, familiar pattern."
            ),
        },
        {
            "name": "Option B — Tabbed View",
            "approach": (
                "Add horizontal tabs above the data section. Each tab shows a different "
                "view or filter of the data. Good for distinct categories."
            ),
        },
        {
            "name": "Option C — Inline Controls + Summary",
            "approach": (
                "Add inline filter controls plus summary/subtotal rows at the bottom. "
                "Users can filter but also see an at-a-glance summary without filtering."
            ),
        },
    ]


# --- Devin-Powered Prototype Generation ---

def get_variant_descriptions() -> list[dict]:
    """Return default variant descriptions (used as context when prototype_results are missing)."""
    return [
        {"key": "A", "name": "Option A — Dropdown Filter", "description": "Simple dropdown to filter."},
        {"key": "B", "name": "Option B — Tabbed View", "description": "Horizontal tabs for each category."},
        {"key": "C", "name": "Option C — Inline Controls + Summary", "description": "Filter controls plus summary rows."},
    ]


def _format_devin_results_for_slack(results: list[dict]) -> list[dict]:
    """Format Devin prototype results into a Slack-friendly format."""
    formatted = []
    for i, result in enumerate(results):
        key = chr(65 + i)  # A, B, C
        structured = result.get("structured_output") or {}
        screenshot_urls = result.get("screenshot_urls", [])

        formatted.append({
            "key": key,
            "name": structured.get("variant_name", result.get("variant_name", f"Option {key}")),
            "description": structured.get("description", result.get("variant_approach", "No description")),
            "session_url": result.get("url", ""),
            "screenshot_urls": screenshot_urls,
            "success": result.get("success", False),
        })

    return formatted


def generate_prototypes(
    feature_description: str,
    client_id: str = "",
    on_session_created: Optional[callable] = None,
    on_variant_complete: Optional[callable] = None,
) -> dict:
    """
    Generate 3 prototype variants using real Devin sessions.

    Each session clones the client project repo, implements one variant,
    runs the app, takes a screenshot, and returns the screenshot URL.

    Returns:
        {
            "mode": "devin",
            "variants": [...],  # list of variant result dicts
        }
    """
    if not devin_integration.is_configured():
        raise RuntimeError(
            "Devin API is not configured. Set DEVIN_API_KEY and CLIENT_PROJECT_REPO in .env."
        )

    print("Using Devin API for prototype generation...")
    variant_approaches = generate_variant_approaches(feature_description)
    client_context = get_context_summary(client_id) if client_id else ""

    sessions = devin_integration.create_prototype_sessions(
        feature_description=feature_description,
        variant_approaches=variant_approaches,
        client_context=client_context,
    )

    if not sessions:
        raise RuntimeError("Failed to create any Devin sessions")

    if on_session_created:
        on_session_created(sessions)

    results = devin_integration.poll_prototype_sessions(
        sessions=sessions,
        on_variant_complete=on_variant_complete,
    )

    return {
        "mode": "devin",
        "variants": _format_devin_results_for_slack(results),
    }
