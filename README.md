# Scope Agent — Client Feature Scoping via Slack

A Slack-based agent that helps B2B SaaS clients articulate feature requests through directed conversation, live visual prototypes, and automatic GitHub issue creation.

## The Problem

At growth-stage B2B SaaS companies, customization requests start vague ("we need better reporting") and take weeks of back-and-forth before anyone understands what to build. The bottleneck isn't engineering — it's the scoping.

## The Solution

A Slack bot that lives in each client's channel and:

1. **Scopes** — asks directed, narrowing questions to turn vague requests into concrete specs
2. **Prototypes** — generates 3 visual variants for the client to compare and choose from
3. **Remembers** — builds a persistent "client model" of preferences, domain context, and history
4. **Hands off** — creates a razor-sharp GitHub issue that an engineer (or AI agent) can execute without ambiguity

## Architecture

```
Client in Slack → Scoping Agent (LLM) → Prototype Generator → GitHub Issue
                        ↕                        ↕
                  Client Model              Screenshots
                (persistent knowledge)    (visual variants)
```

### Components

| Component | Path | Description |
|---|---|---|
| **Slack Bot** | `slackbot/app.py` | Main app — routes messages, manages conversation state |
| **Scoping Agent** | `slackbot/scoping_agent.py` | LLM-powered conversation that narrows requests |
| **Prototype Generator** | `slackbot/prototype_generator.py` | Generates 3 HTML variant screenshots via Playwright |
| **GitHub Issue Creator** | `slackbot/github_issue.py` | Creates well-formatted issues from the final spec |
| **Client Model** | `slackbot/client_model.py` | Persistent per-client knowledge (preferences, history) |
| **Devin Integration** | `slackbot/devin_integration.py` | Production upgrade: real Devin API for prototype generation |
| **Sample App** | `sample-app/` | React dashboard (the app being customized) |

## Quick Start

### 1. Install dependencies

```bash
cd slackbot
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your credentials
```

### 3. Run in demo mode (no Slack needed)

```bash
python app.py
```

This starts an interactive terminal demo where you can test the scoping conversation flow.

### 4. Run with Slack

Create a Slack app at https://api.slack.com/apps with:
- **Bot Token Scopes**: `app_mentions:read`, `chat:write`, `files:write`, `channels:read`
- **Event Subscriptions**: `app_mention`, `message.channels`
- **Socket Mode** enabled

Then set your env vars and run:

```bash
python app.py
```

### 5. Run the sample dashboard app

```bash
cd sample-app
npm install
npm run dev
# Opens at http://localhost:3000
```

## Configuration

| Variable | Required | Description |
|---|---|---|
| `SLACK_BOT_TOKEN` | For Slack | Bot token (xoxb-...) |
| `SLACK_SIGNING_SECRET` | For Slack | Signing secret |
| `SLACK_APP_TOKEN` | For Slack | App token for Socket Mode (xapp-...) |
| `OPENAI_API_KEY` | Optional | For LLM-powered scoping (falls back to demo mode) |
| `GITHUB_TOKEN` | Optional | For GitHub issue creation (falls back to preview mode) |
| `GITHUB_REPO` | Optional | Target repo in owner/repo format |
| `DEVIN_API_KEY` | Optional | For production prototype generation via Devin API |

## How It Works

### Conversation Flow

```
Client: "We need better reporting"
                │
Agent: "Are you looking to A) filter existing data, B) add new metrics, or C) change the layout?"
                │
Client: "Filter by tier"
                │
Agent: "Dropdown filter, tabs, or both with subtotals? [narrows further]"
                │
Client: "Dropdown with subtotals"
                │
Agent: "Generating 3 prototypes..." → [Screenshot A] [Screenshot B] [Screenshot C]
                │
Client: "I like Option C"
                │
Agent: "Here's the final spec. Confirm to submit?"
                │
Client: "Confirm"
                │
→ GitHub Issue created with razor-sharp spec
→ Client model updated with preferences
```

### Client Model

Each client's preferences and context accumulate over time in `client-models/{client_id}.json`:

```json
{
  "client_id": "acme",
  "preferences": {
    "preferred_patterns": ["dropdown filters", "subtotal rows"],
    "rejected_patterns": ["accordion views"]
  },
  "domain_context": {
    "contract_tiers": ["Gold", "Silver", "Bronze"]
  },
  "request_history": [...]
}
```

### Production Upgrade: Devin API

The prototype generator can be swapped from local HTML/Playwright to real Devin sessions:

```python
# Instead of local screenshots, spin up 3 parallel Devin sessions:
POST /v3/organizations/sessions
{
  "prompt": "Implement tier filter variant A for the MRR table...",
  "playbook_id": "client-prototype-playbook",
  "session_secrets": [{"key": "DEPLOY_TOKEN", "value": "..."}]
}
```

Each session builds a real feature branch, deploys a preview, and returns structured output with the preview URL.

## Sample App

The `sample-app/` directory contains a React dashboard (built with Vite) that simulates a B2B SaaS product:

- **MRR Table** — Monthly Recurring Revenue broken down by contract tier
- **Client Table** — Client overview with tier, MRR, seats, and join date

This is the app that clients would be requesting customizations for.
