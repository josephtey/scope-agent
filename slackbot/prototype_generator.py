"""
Prototype Generator — creates visual variants of dashboard features.

Two modes:
1. DEVIN MODE (production): Spins up 3 parallel Devin sessions via the API,
   each implementing a different variant of the requested feature on the real
   client project repo (josephtey/sample-client-project).
2. LOCAL MODE (fallback): Generates static HTML screenshots via Playwright
   when the Devin API is unavailable.

The scoping agent decides when to prototype and provides the feature description.
This module generates 3 variant approaches and either delegates to Devin or
renders local previews.
"""

import os
import json
import asyncio
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

def generate_prototypes_with_devin(
    feature_description: str,
    client_id: str = "",
    on_session_created: Optional[callable] = None,
    on_variant_complete: Optional[callable] = None,
) -> list[dict]:
    """
    Generate 3 prototype variants using real Devin sessions.

    Each session clones the client project repo, implements one variant,
    creates a PR, and returns structured output with details.

    Args:
        feature_description: The scoped feature request
        client_id: Client ID for loading preferences
        on_session_created: Callback(sessions_list) when sessions are created
        on_variant_complete: Callback(result) for each completed variant

    Returns list of result dicts with variant info, PR URLs, etc.
    """
    variant_approaches = generate_variant_approaches(feature_description)
    client_context = get_context_summary(client_id) if client_id else ""

    # Create 3 parallel Devin sessions
    sessions = devin_integration.create_prototype_sessions(
        feature_description=feature_description,
        variant_approaches=variant_approaches,
        client_context=client_context,
    )

    if not sessions:
        print("No Devin sessions created — all failed")
        return []

    if on_session_created:
        on_session_created(sessions)

    # Poll until all complete
    results = devin_integration.poll_prototype_sessions(
        sessions=sessions,
        on_variant_complete=on_variant_complete,
    )

    return results


def format_devin_results_for_slack(results: list[dict]) -> list[dict]:
    """
    Format Devin prototype results into a Slack-friendly format.

    Returns list of dicts with: key, name, description, pr_url, session_url
    """
    formatted = []
    for i, result in enumerate(results):
        key = chr(65 + i)  # A, B, C
        structured = result.get("structured_output") or {}
        # v1 API returns pull_request (singular object with url), not pull_requests array
        pr_info = result.get("pull_request") or {}
        pr_url = pr_info.get("url", "") if isinstance(pr_info, dict) else ""

        formatted.append({
            "key": key,
            "name": structured.get("variant_name", result.get("variant_name", f"Option {key}")),
            "description": structured.get("description", result.get("variant_approach", "No description")),
            "pr_url": pr_url,
            "session_url": result.get("url", ""),
            "files_changed": structured.get("files_changed", []),
            "screenshot_url": structured.get("screenshot_url", ""),
            "preview_url": structured.get("preview_url", ""),
            "success": result.get("success", False),
        })

    return formatted


# --- Local Fallback (static HTML + Playwright screenshots) ---

FALLBACK_VARIANT_A_HTML = """<!DOCTYPE html>
<html><head><style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f7fa; padding: 32px; }
.card { background: white; border-radius: 12px; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); max-width: 900px; margin: 0 auto; }
h2 { font-size: 16px; font-weight: 600; margin-bottom: 16px; color: #444; }
.label { font-size: 12px; font-weight: 600; color: #666; text-transform: uppercase; margin-bottom: 6px; }
select { padding: 8px 12px; border: 1px solid #e0e0e0; border-radius: 8px; font-size: 14px; margin-bottom: 16px; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th { text-align: left; padding: 10px 12px; border-bottom: 2px solid #e8eaed; font-weight: 600; color: #666; font-size: 12px; text-transform: uppercase; }
td { padding: 10px 12px; border-bottom: 1px solid #f0f0f0; }
.val { font-weight: 600; } .total { font-weight: 700; color: #1a1a2e; }
.approach-label { font-size: 13px; color: #6366f1; font-weight: 600; margin-bottom: 12px; }
</style></head><body>
<div class="card">
  <div class="approach-label">Option A — Dropdown Filter</div>
  <h2>Monthly Recurring Revenue</h2>
  <div class="label">Filter by Tier</div>
  <select><option selected>All Tiers</option><option>Gold</option><option>Silver</option><option>Bronze</option></select>
  <table>
    <thead><tr><th>Month</th><th>Total MRR</th><th>Gold</th><th>Silver</th><th>Bronze</th></tr></thead>
    <tbody>
      <tr><td>Sep 2025</td><td class="val total">$72,000</td><td class="val">$38,000</td><td class="val">$24,000</td><td class="val">$10,000</td></tr>
      <tr><td>Oct 2025</td><td class="val total">$75,200</td><td class="val">$39,500</td><td class="val">$25,200</td><td class="val">$10,500</td></tr>
      <tr><td>Nov 2025</td><td class="val total">$78,100</td><td class="val">$41,000</td><td class="val">$26,600</td><td class="val">$10,500</td></tr>
    </tbody>
  </table>
</div></body></html>"""

FALLBACK_VARIANT_B_HTML = """<!DOCTYPE html>
<html><head><style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f7fa; padding: 32px; }
.card { background: white; border-radius: 12px; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); max-width: 900px; margin: 0 auto; }
h2 { font-size: 16px; font-weight: 600; margin-bottom: 16px; color: #444; }
.tabs { display: flex; gap: 0; margin-bottom: 16px; border-bottom: 2px solid #e8eaed; }
.tab { padding: 10px 20px; font-size: 14px; font-weight: 500; cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -2px; color: #888; }
.tab.active { color: #1a1a2e; border-bottom-color: #6366f1; font-weight: 600; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th { text-align: left; padding: 10px 12px; border-bottom: 2px solid #e8eaed; font-weight: 600; color: #666; font-size: 12px; text-transform: uppercase; }
td { padding: 10px 12px; border-bottom: 1px solid #f0f0f0; }
.val { font-weight: 600; } .total { font-weight: 700; color: #1a1a2e; }
.approach-label { font-size: 13px; color: #6366f1; font-weight: 600; margin-bottom: 12px; }
</style></head><body>
<div class="card">
  <div class="approach-label">Option B — Tabbed View by Tier</div>
  <h2>Monthly Recurring Revenue</h2>
  <div class="tabs"><div class="tab active">All Tiers</div><div class="tab">Gold</div><div class="tab">Silver</div><div class="tab">Bronze</div></div>
  <table>
    <thead><tr><th>Month</th><th>Total MRR</th><th>Gold</th><th>Silver</th><th>Bronze</th></tr></thead>
    <tbody>
      <tr><td>Sep 2025</td><td class="val total">$72,000</td><td class="val">$38,000</td><td class="val">$24,000</td><td class="val">$10,000</td></tr>
      <tr><td>Oct 2025</td><td class="val total">$75,200</td><td class="val">$39,500</td><td class="val">$25,200</td><td class="val">$10,500</td></tr>
      <tr><td>Nov 2025</td><td class="val total">$78,100</td><td class="val">$41,000</td><td class="val">$26,600</td><td class="val">$10,500</td></tr>
    </tbody>
  </table>
</div></body></html>"""

FALLBACK_VARIANT_C_HTML = """<!DOCTYPE html>
<html><head><style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f7fa; padding: 32px; }
.card { background: white; border-radius: 12px; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); max-width: 900px; margin: 0 auto; }
h2 { font-size: 16px; font-weight: 600; margin-bottom: 16px; color: #444; }
.label { font-size: 12px; font-weight: 600; color: #666; text-transform: uppercase; margin-bottom: 6px; }
select { padding: 8px 12px; border: 1px solid #e0e0e0; border-radius: 8px; font-size: 14px; margin-bottom: 16px; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th { text-align: left; padding: 10px 12px; border-bottom: 2px solid #e8eaed; font-weight: 600; color: #666; font-size: 12px; text-transform: uppercase; }
td { padding: 10px 12px; border-bottom: 1px solid #f0f0f0; }
.val { font-weight: 600; } .total { font-weight: 700; color: #1a1a2e; }
.subtotal td { background: #f8f9fb; font-weight: 600; border-top: 1px solid #e0e0e0; }
.subtotal .tier-label { color: #6366f1; font-size: 12px; text-transform: uppercase; }
.approach-label { font-size: 13px; color: #6366f1; font-weight: 600; margin-bottom: 12px; }
</style></head><body>
<div class="card">
  <div class="approach-label">Option C — Dropdown + Subtotal Rows</div>
  <h2>Monthly Recurring Revenue</h2>
  <div class="label">Filter by Tier</div>
  <select><option selected>All Tiers</option><option>Gold</option><option>Silver</option><option>Bronze</option></select>
  <table>
    <thead><tr><th>Month</th><th>Total MRR</th><th>Gold</th><th>Silver</th><th>Bronze</th></tr></thead>
    <tbody>
      <tr><td>Sep 2025</td><td class="val total">$72,000</td><td class="val">$38,000</td><td class="val">$24,000</td><td class="val">$10,000</td></tr>
      <tr><td>Oct 2025</td><td class="val total">$75,200</td><td class="val">$39,500</td><td class="val">$25,200</td><td class="val">$10,500</td></tr>
      <tr><td>Nov 2025</td><td class="val total">$78,100</td><td class="val">$41,000</td><td class="val">$26,600</td><td class="val">$10,500</td></tr>
      <tr class="subtotal"><td class="tier-label">GOLD SUBTOTAL</td><td class="val">$251,500</td><td></td><td></td><td></td></tr>
      <tr class="subtotal"><td class="tier-label">SILVER SUBTOTAL</td><td class="val">$164,800</td><td></td><td></td><td></td></tr>
      <tr class="subtotal"><td class="tier-label">BRONZE SUBTOTAL</td><td class="val">$62,100</td><td></td><td></td><td></td></tr>
    </tbody>
  </table>
</div></body></html>"""

FALLBACK_VARIANTS = {
    "A": {
        "name": "Option A — Dropdown Filter",
        "description": "Simple dropdown at the top of the MRR table. Select a tier to filter, or 'All' to see everything. Clean and minimal.",
        "html": FALLBACK_VARIANT_A_HTML,
    },
    "B": {
        "name": "Option B — Tabbed View",
        "description": "Horizontal tabs for each tier. Click a tab to switch views. Familiar pattern, but takes more horizontal space.",
        "html": FALLBACK_VARIANT_B_HTML,
    },
    "C": {
        "name": "Option C — Dropdown + Subtotal Rows",
        "description": "Dropdown filter plus subtotal rows at the bottom showing totals per tier. Best of both worlds — filter when needed, summary always visible.",
        "html": FALLBACK_VARIANT_C_HTML,
    },
}


def get_variant_descriptions() -> list[dict]:
    """Return descriptions of fallback variants (for local/demo mode)."""
    return [
        {"key": key, "name": v["name"], "description": v["description"]}
        for key, v in FALLBACK_VARIANTS.items()
    ]


async def generate_screenshots(output_dir: str) -> dict[str, str]:
    """
    Generate local fallback screenshots using Playwright.
    Returns a dict mapping variant key to screenshot file path.
    """
    os.makedirs(output_dir, exist_ok=True)
    paths = {}

    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            for key, variant in FALLBACK_VARIANTS.items():
                page = await browser.new_page(viewport={"width": 960, "height": 600})
                await page.set_content(variant["html"])
                await page.wait_for_timeout(500)

                screenshot_path = os.path.join(output_dir, f"variant_{key.lower()}.png")
                await page.screenshot(path=screenshot_path, full_page=True)
                paths[key] = screenshot_path

            await browser.close()
    except Exception as e:
        print(f"Playwright screenshot failed ({e}), falling back to HTML files")
        for key, variant in FALLBACK_VARIANTS.items():
            html_path = os.path.join(output_dir, f"variant_{key.lower()}.html")
            with open(html_path, "w") as f:
                f.write(variant["html"])
            paths[key] = html_path

    return paths


def generate_screenshots_sync(output_dir: str) -> dict[str, str]:
    """Synchronous wrapper for generate_screenshots."""
    return asyncio.run(generate_screenshots(output_dir))


# --- Unified Interface ---

def should_use_devin() -> bool:
    """Check if we should use real Devin sessions or fall back to local."""
    return devin_integration.is_configured()


def generate_prototypes(
    feature_description: str,
    client_id: str = "",
    output_dir: str = "",
    on_session_created: Optional[callable] = None,
    on_variant_complete: Optional[callable] = None,
) -> dict:
    """
    Unified prototype generation — uses Devin if available, falls back to local.

    Returns:
        {
            "mode": "devin" | "local",
            "variants": [...],  # list of variant result dicts
        }
    """
    if should_use_devin():
        print("Using Devin API for prototype generation...")
        results = generate_prototypes_with_devin(
            feature_description=feature_description,
            client_id=client_id,
            on_session_created=on_session_created,
            on_variant_complete=on_variant_complete,
        )
        if results:
            return {
                "mode": "devin",
                "variants": format_devin_results_for_slack(results),
            }
        print("Devin sessions failed — falling back to local generation")

    # Local fallback
    print("Using local Playwright for prototype generation...")
    if not output_dir:
        import tempfile
        output_dir = tempfile.mkdtemp(prefix="scope_agent_variants_")

    paths = generate_screenshots_sync(output_dir)
    variants = []
    for key, variant in FALLBACK_VARIANTS.items():
        variants.append({
            "key": key,
            "name": variant["name"],
            "description": variant["description"],
            "screenshot_path": paths.get(key, ""),
            "success": True,
        })

    return {
        "mode": "local",
        "variants": variants,
    }
