"""
Scoping Agent — the LLM-powered conversational layer that turns vague
client requests into concrete, well-scoped feature specifications.

The agent reads the client model for context, asks directed narrowing
questions, and decides when a request is specific enough to prototype.
"""

import json
from typing import Optional

import anthropic

import config
from client_model import get_context_summary, load_model

SYSTEM_PROMPT = """You are a scoping agent for a B2B SaaS company called GrowthOps.
Your job is to help clients articulate exactly what they want for feature customizations.

You are talking directly to the client in a Slack channel. Be friendly, conversational, and curious.

RULES:
1. Ask directed, narrowing questions — NOT open-ended "tell me more."
2. Offer constrained choices when possible (A or B? filter or separate view?).
3. Reference what you know about the client from the context provided.
4. IMPORTANT: Do NOT rush to [READY_TO_PROTOTYPE]. Ask AT LEAST 3-4 rounds of clarifying questions first.
   You want to deeply understand:
   - What specific part of the app they're referring to
   - What problem they're trying to solve (the "why" behind the request)
   - What their preferred UI pattern is (dropdown, tabs, cards, etc.)
   - Any constraints or things they explicitly do NOT want
   - How this fits into their workflow
   Only say [READY_TO_PROTOTYPE] once you have a crystal-clear picture.
5. After prototypes are shown and client confirms, say EXACTLY: [READY_TO_SUBMIT]
6. Never make assumptions — always confirm with the client.
7. Keep responses concise — 2-3 sentences max per message.
8. Be warm and collaborative — this should feel like brainstorming with a smart colleague,
   not filling out a form.

THE CLIENT'S APP:
The client uses a B2B SaaS dashboard. Here's what's in the app (describe these in plain
language — NEVER mention file names, component names, code, or technical terms to the client):

Pages & sections:
- A left-hand navigation sidebar with links to: Dashboard, Clients, Feature Requests, Billing, Settings
- A row of summary cards at the top showing: Total MRR, Active Clients, Total Seats, Open Requests
- A revenue table showing monthly recurring revenue broken down by tier (Gold, Silver, Bronze)
- A client overview table showing each client's name, tier, MRR, seats, usage, and join date
- A feature requests tracker showing each request's title, client, priority, status, and date

Key data:
- 3 contract tiers: Gold ($5,000+), Silver ($2,000–$4,999), Bronze (under $2,000)
- 12 clients across those tiers
- 6 months of MRR history
- 8 tracked feature requests with priority levels (High/Medium/Low) and statuses (Open/In Progress/Completed)

IMPORTANT: You are talking to a non-technical business user. NEVER reference file names (like
"MRRTable.jsx"), component names, code, React, Vite, or any implementation details. Always
describe things from the user's perspective — e.g., say "the revenue table" not "MRRTable.jsx",
say "the client list" not "ClientTable.jsx".

ABOUT THE PROTOTYPE PHASE:
When you say [READY_TO_PROTOTYPE], the system will generate 3 visual mockup screenshots.
The client will see the screenshots and pick one or give feedback. Use their feedback to refine.
You may go through multiple prototype rounds.
Do NOT mention "Devin", "sessions", "PRs", or any technical implementation details to the client.
Just tell them you're going to sketch up a few ideas for them to look at.

ABOUT THE SUBMISSION PHASE:
When you say [READY_TO_SUBMIT], provide a structured feature spec in this EXACT format:

```json
{
  "title": "Short descriptive title",
  "description": "One paragraph describing what to build",
  "target_area": "which part of the app (e.g. revenue table, client list, sidebar)",
  "requirements": ["specific requirement 1", "specific requirement 2"],
  "out_of_scope": ["what NOT to build"],
  "client_preferences": ["UI/UX preferences noted during conversation"],
  "complexity_estimate": "small|medium|large"
}
```
"""


def create_client() -> Optional[anthropic.Anthropic]:
    """Create an Anthropic client if API key is configured."""
    if not config.ANTHROPIC_API_KEY:
        return None
    return anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)


def build_messages(
    client_id: str,
    conversation_history: list[dict],
    user_message: str,
) -> list[dict]:
    """Build the full message list for the LLM call."""
    client_context = get_context_summary(client_id)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "system",
            "content": f"CLIENT CONTEXT:\n{client_context}",
        },
    ]

    # Add conversation history
    for msg in conversation_history:
        messages.append(msg)

    # Add the new user message
    messages.append({"role": "user", "content": user_message})

    return messages


def get_response(
    client_id: str,
    conversation_history: list[dict],
    user_message: str,
) -> str:
    """Get the scoping agent's response to the client's message."""
    client = create_client()

    if client is None:
        # Fallback: simulated scoping conversation for demo
        return _simulated_response(conversation_history, user_message)

    messages = build_messages(client_id, conversation_history, user_message)

    # Anthropic requires system prompt separate from messages
    system_content = ""
    chat_messages = []
    for msg in messages:
        if msg["role"] == "system":
            system_content += msg["content"] + "\n\n"
        else:
            chat_messages.append(msg)

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        system=system_content.strip(),
        messages=chat_messages,
        temperature=0.7,
        max_tokens=500,
    )

    return response.content[0].text


def extract_feature_spec(response_text: str) -> Optional[dict]:
    """Extract the JSON feature spec from a [READY_TO_SUBMIT] response."""
    if "```json" in response_text:
        start = response_text.index("```json") + 7
        end = response_text.index("```", start)
        json_str = response_text[start:end].strip()
        return json.loads(json_str)
    return None


def is_ready_to_prototype(response_text: str) -> bool:
    """Check if the agent thinks the request is specific enough to prototype."""
    return "[READY_TO_PROTOTYPE]" in response_text


def is_ready_to_submit(response_text: str) -> bool:
    """Check if the agent is ready to submit the final feature request."""
    return "[READY_TO_SUBMIT]" in response_text


# --- Simulated responses for demo mode (no OpenAI key) ---

_DEMO_RESPONSES = [
    {
        "keywords": ["reporting", "report", "dashboard", "mrr", "revenue"],
        "response": (
            "Got it — you're looking at the revenue dashboard. Are you wanting to:\n"
            "A) Add a new way to filter/break down the existing MRR table?\n"
            "B) Add a completely new metric or chart?\n"
            "C) Change how the client overview table displays data?"
        ),
    },
    {
        "keywords": ["filter", "break down", "breakdown", "tier", "a)"],
        "response": (
            "A tier filter on the MRR table — nice. A few options:\n"
            "1. **Dropdown filter** — select a tier, table filters to just that tier\n"
            "2. **Subtotal rows** — keep all data visible but add subtotal rows per tier\n"
            "3. **Both** — dropdown filter + subtotal rows when showing all\n\n"
            "Which feels right?"
        ),
    },
    {
        "keywords": ["both", "3", "subtotal", "dropdown"],
        "response": (
            "Great choice. To confirm: dropdown filter at the top of the MRR table, "
            "and when 'All' is selected, subtotal rows appear for each tier. "
            "When a specific tier is selected, only that tier's data shows.\n\n"
            "Does that match what you're thinking? If yes, I'll generate some visual prototypes for you.\n\n"
            "[READY_TO_PROTOTYPE]"
        ),
    },
    {
        "keywords": ["yes", "correct", "right", "looks good", "that's it", "perfect"],
        "response": (
            "Glad that matches! Let me spin up a few visual options for you to compare..."
        ),
    },
    {
        "keywords": ["option", "like", "prefer", "pick", "go with"],
        "response": (
            "Noted your preference. I've captured everything — here's the final spec "
            "I'll send to the engineering team:\n\n"
            "[READY_TO_SUBMIT]\n\n"
            '```json\n'
            '{\n'
            '  "title": "Add tier filter with subtotals to MRR dashboard table",\n'
            '  "description": "Add a dropdown filter for contract tier (Gold/Silver/Bronze/All) to the MRR table. '
            'When All is selected, display subtotal rows per tier. When a specific tier is selected, '
            'filter the table to show only that tier\'s data.",\n'
            '  "target_component": "MRR table (src/components/MRRTable.jsx)",\n'
            '  "requirements": [\n'
            '    "Dropdown filter with options: All, Gold, Silver, Bronze",\n'
            '    "Subtotal rows per tier when All is selected",\n'
            '    "Table filters to single tier when selected",\n'
            '    "Maintain existing column layout (Month, Total MRR, Gold, Silver, Bronze)",\n'
            '    "Smooth transition when switching filters"\n'
            '  ],\n'
            '  "out_of_scope": [\n'
            '    "No new pages or views",\n'
            '    "No chart/visualization changes",\n'
            '    "No changes to underlying data model"\n'
            '  ],\n'
            '  "client_preferences": [\n'
            '    "Prefers dropdown filter over tabs",\n'
            '    "Wants subtotal rows for at-a-glance comparison",\n'
            '    "Values simplicity over feature density"\n'
            '  ],\n'
            '  "complexity_estimate": "small"\n'
            '}\n'
            '```'
        ),
    },
]

_DEMO_FALLBACK = (
    "Could you be more specific? For example, which part of the dashboard "
    "are you referring to — the MRR table, the client overview, or something else?"
)


def _simulated_response(conversation_history: list[dict], user_message: str) -> str:
    """Provide a simulated response for demo mode without an LLM."""
    msg_lower = user_message.lower()

    # Check how far along we are in the conversation
    num_exchanges = len([m for m in conversation_history if m["role"] == "assistant"])

    for demo in _DEMO_RESPONSES:
        if any(kw in msg_lower for kw in demo["keywords"]):
            return demo["response"]

    return _DEMO_FALLBACK
