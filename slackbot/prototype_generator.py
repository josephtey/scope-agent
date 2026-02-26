"""
Prototype Generator — creates visual variants of dashboard features.

For the prototype, we generate 3 different HTML variants of the requested
feature and capture screenshots using Playwright. In production, this would
spin up 3 parallel Devin sessions via the API.

Each variant represents a different UI approach to the same feature request.
"""

import os
import asyncio
from typing import Optional

# Variant HTML templates for the MRR tier filter feature
# These simulate what Devin would build as prototypes

VARIANT_A_HTML = """
<!DOCTYPE html>
<html>
<head>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f7fa; padding: 32px; }
.card { background: white; border-radius: 12px; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); max-width: 900px; margin: 0 auto; }
h2 { font-size: 16px; font-weight: 600; margin-bottom: 16px; color: #444; }
.label { font-size: 12px; font-weight: 600; color: #666; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; }
select { padding: 8px 12px; border: 1px solid #e0e0e0; border-radius: 8px; font-size: 14px; margin-bottom: 16px; background: white; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th { text-align: left; padding: 10px 12px; border-bottom: 2px solid #e8eaed; font-weight: 600; color: #666; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; }
td { padding: 10px 12px; border-bottom: 1px solid #f0f0f0; }
.val { font-weight: 600; font-variant-numeric: tabular-nums; }
.total { font-weight: 700; color: #1a1a2e; }
.badge { display: inline-block; font-size: 11px; padding: 2px 8px; border-radius: 4px; font-weight: 600; color: white; background: #6366f1; margin-left: 8px; }
.approach-label { font-size: 13px; color: #6366f1; font-weight: 600; margin-bottom: 12px; }
</style>
</head>
<body>
<div class="card">
  <div class="approach-label">Option A — Dropdown Filter</div>
  <h2>Monthly Recurring Revenue</h2>
  <div class="label">Filter by Tier</div>
  <select>
    <option selected>All Tiers</option>
    <option>Gold</option>
    <option>Silver</option>
    <option>Bronze</option>
  </select>
  <table>
    <thead><tr><th>Month</th><th>Total MRR</th><th>Gold</th><th>Silver</th><th>Bronze</th></tr></thead>
    <tbody>
      <tr><td>Sep 2025</td><td class="val total">$72,000</td><td class="val">$38,000</td><td class="val">$24,000</td><td class="val">$10,000</td></tr>
      <tr><td>Oct 2025</td><td class="val total">$75,200</td><td class="val">$39,500</td><td class="val">$25,200</td><td class="val">$10,500</td></tr>
      <tr><td>Nov 2025</td><td class="val total">$78,100</td><td class="val">$41,000</td><td class="val">$26,600</td><td class="val">$10,500</td></tr>
      <tr><td>Dec 2025</td><td class="val total">$81,400</td><td class="val">$43,000</td><td class="val">$27,900</td><td class="val">$10,500</td></tr>
      <tr><td>Jan 2026</td><td class="val total">$84,500</td><td class="val">$44,500</td><td class="val">$29,500</td><td class="val">$10,500</td></tr>
      <tr><td>Feb 2026</td><td class="val total">$87,200</td><td class="val">$45,500</td><td class="val">$31,600</td><td class="val">$10,100</td></tr>
    </tbody>
  </table>
</div>
</body>
</html>
"""

VARIANT_B_HTML = """
<!DOCTYPE html>
<html>
<head>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f7fa; padding: 32px; }
.card { background: white; border-radius: 12px; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); max-width: 900px; margin: 0 auto; }
h2 { font-size: 16px; font-weight: 600; margin-bottom: 16px; color: #444; }
.tabs { display: flex; gap: 0; margin-bottom: 16px; border-bottom: 2px solid #e8eaed; }
.tab { padding: 10px 20px; font-size: 14px; font-weight: 500; cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -2px; color: #888; }
.tab.active { color: #1a1a2e; border-bottom-color: #6366f1; font-weight: 600; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th { text-align: left; padding: 10px 12px; border-bottom: 2px solid #e8eaed; font-weight: 600; color: #666; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; }
td { padding: 10px 12px; border-bottom: 1px solid #f0f0f0; }
.val { font-weight: 600; font-variant-numeric: tabular-nums; }
.total { font-weight: 700; color: #1a1a2e; }
.approach-label { font-size: 13px; color: #6366f1; font-weight: 600; margin-bottom: 12px; }
</style>
</head>
<body>
<div class="card">
  <div class="approach-label">Option B — Tabbed View by Tier</div>
  <h2>Monthly Recurring Revenue</h2>
  <div class="tabs">
    <div class="tab active">All Tiers</div>
    <div class="tab">Gold</div>
    <div class="tab">Silver</div>
    <div class="tab">Bronze</div>
  </div>
  <table>
    <thead><tr><th>Month</th><th>Total MRR</th><th>Gold</th><th>Silver</th><th>Bronze</th></tr></thead>
    <tbody>
      <tr><td>Sep 2025</td><td class="val total">$72,000</td><td class="val">$38,000</td><td class="val">$24,000</td><td class="val">$10,000</td></tr>
      <tr><td>Oct 2025</td><td class="val total">$75,200</td><td class="val">$39,500</td><td class="val">$25,200</td><td class="val">$10,500</td></tr>
      <tr><td>Nov 2025</td><td class="val total">$78,100</td><td class="val">$41,000</td><td class="val">$26,600</td><td class="val">$10,500</td></tr>
      <tr><td>Dec 2025</td><td class="val total">$81,400</td><td class="val">$43,000</td><td class="val">$27,900</td><td class="val">$10,500</td></tr>
      <tr><td>Jan 2026</td><td class="val total">$84,500</td><td class="val">$44,500</td><td class="val">$29,500</td><td class="val">$10,500</td></tr>
      <tr><td>Feb 2026</td><td class="val total">$87,200</td><td class="val">$45,500</td><td class="val">$31,600</td><td class="val">$10,100</td></tr>
    </tbody>
  </table>
</div>
</body>
</html>
"""

VARIANT_C_HTML = """
<!DOCTYPE html>
<html>
<head>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f7fa; padding: 32px; }
.card { background: white; border-radius: 12px; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); max-width: 900px; margin: 0 auto; }
h2 { font-size: 16px; font-weight: 600; margin-bottom: 16px; color: #444; }
.label { font-size: 12px; font-weight: 600; color: #666; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; }
select { padding: 8px 12px; border: 1px solid #e0e0e0; border-radius: 8px; font-size: 14px; margin-bottom: 16px; background: white; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th { text-align: left; padding: 10px 12px; border-bottom: 2px solid #e8eaed; font-weight: 600; color: #666; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; }
td { padding: 10px 12px; border-bottom: 1px solid #f0f0f0; }
.val { font-weight: 600; font-variant-numeric: tabular-nums; }
.total { font-weight: 700; color: #1a1a2e; }
.subtotal td { background: #f8f9fb; font-weight: 600; border-top: 1px solid #e0e0e0; }
.subtotal .tier-label { color: #6366f1; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; }
.approach-label { font-size: 13px; color: #6366f1; font-weight: 600; margin-bottom: 12px; }
</style>
</head>
<body>
<div class="card">
  <div class="approach-label">Option C — Dropdown Filter + Subtotal Rows</div>
  <h2>Monthly Recurring Revenue</h2>
  <div class="label">Filter by Tier</div>
  <select>
    <option selected>All Tiers</option>
    <option>Gold</option>
    <option>Silver</option>
    <option>Bronze</option>
  </select>
  <table>
    <thead><tr><th>Month</th><th>Total MRR</th><th>Gold</th><th>Silver</th><th>Bronze</th></tr></thead>
    <tbody>
      <tr><td>Sep 2025</td><td class="val total">$72,000</td><td class="val">$38,000</td><td class="val">$24,000</td><td class="val">$10,000</td></tr>
      <tr><td>Oct 2025</td><td class="val total">$75,200</td><td class="val">$39,500</td><td class="val">$25,200</td><td class="val">$10,500</td></tr>
      <tr><td>Nov 2025</td><td class="val total">$78,100</td><td class="val">$41,000</td><td class="val">$26,600</td><td class="val">$10,500</td></tr>
      <tr><td>Dec 2025</td><td class="val total">$81,400</td><td class="val">$43,000</td><td class="val">$27,900</td><td class="val">$10,500</td></tr>
      <tr><td>Jan 2026</td><td class="val total">$84,500</td><td class="val">$44,500</td><td class="val">$29,500</td><td class="val">$10,500</td></tr>
      <tr><td>Feb 2026</td><td class="val total">$87,200</td><td class="val">$45,500</td><td class="val">$31,600</td><td class="val">$10,100</td></tr>
      <tr class="subtotal"><td class="tier-label">GOLD SUBTOTAL</td><td class="val">$251,500</td><td></td><td></td><td></td></tr>
      <tr class="subtotal"><td class="tier-label">SILVER SUBTOTAL</td><td class="val">$164,800</td><td></td><td></td><td></td></tr>
      <tr class="subtotal"><td class="tier-label">BRONZE SUBTOTAL</td><td class="val">$62,100</td><td></td><td></td><td></td></tr>
    </tbody>
  </table>
</div>
</body>
</html>
"""

VARIANTS = {
    "A": {
        "name": "Option A — Dropdown Filter",
        "description": "Simple dropdown at the top of the MRR table. Select a tier to filter, or 'All' to see everything. Clean and minimal.",
        "html": VARIANT_A_HTML,
    },
    "B": {
        "name": "Option B — Tabbed View",
        "description": "Horizontal tabs for each tier. Click a tab to switch views. Familiar pattern, but takes more horizontal space.",
        "html": VARIANT_B_HTML,
    },
    "C": {
        "name": "Option C — Dropdown + Subtotal Rows",
        "description": "Dropdown filter plus subtotal rows at the bottom showing totals per tier. Best of both worlds — filter when needed, summary always visible.",
        "html": VARIANT_C_HTML,
    },
}


def get_variant_descriptions() -> list[dict]:
    """Return descriptions of all variants (without HTML)."""
    return [
        {"key": key, "name": v["name"], "description": v["description"]}
        for key, v in VARIANTS.items()
    ]


async def generate_screenshots(output_dir: str) -> dict[str, str]:
    """
    Generate screenshots of all 3 variants using Playwright.
    Returns a dict mapping variant key to screenshot file path.
    """
    os.makedirs(output_dir, exist_ok=True)
    paths = {}

    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            for key, variant in VARIANTS.items():
                page = await browser.new_page(viewport={"width": 960, "height": 600})
                await page.set_content(variant["html"])
                await page.wait_for_timeout(500)

                screenshot_path = os.path.join(output_dir, f"variant_{key.lower()}.png")
                await page.screenshot(path=screenshot_path, full_page=True)
                paths[key] = screenshot_path

            await browser.close()
    except Exception as e:
        # Fallback: write HTML files instead of screenshots
        print(f"Playwright screenshot failed ({e}), falling back to HTML files")
        for key, variant in VARIANTS.items():
            html_path = os.path.join(output_dir, f"variant_{key.lower()}.html")
            with open(html_path, "w") as f:
                f.write(variant["html"])
            paths[key] = html_path

    return paths


def generate_screenshots_sync(output_dir: str) -> dict[str, str]:
    """Synchronous wrapper for generate_screenshots."""
    return asyncio.run(generate_screenshots(output_dir))
