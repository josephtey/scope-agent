import os
from dotenv import load_dotenv

load_dotenv()

# Slack
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET", "")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN", "")

# OpenAI
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# GitHub
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "josephtey/sample-client-project")

# Devin API
DEVIN_API_KEY = os.environ.get("DEVIN_API_KEY", "")

# The client project repo that Devin will fork/modify for prototypes
CLIENT_PROJECT_REPO = os.environ.get("CLIENT_PROJECT_REPO", "josephtey/sample-client-project")

# Devin playbook ID for prototype generation (created via API or UI)
PROTOTYPE_PLAYBOOK_ID = os.environ.get("PROTOTYPE_PLAYBOOK_ID", "")

# Sample app URL (for local screenshot fallback)
SAMPLE_APP_URL = os.environ.get("SAMPLE_APP_URL", "http://localhost:3000")

# Devin session poll interval and timeout
DEVIN_POLL_INTERVAL = int(os.environ.get("DEVIN_POLL_INTERVAL", "15"))
DEVIN_SESSION_TIMEOUT = int(os.environ.get("DEVIN_SESSION_TIMEOUT", "600"))

# Client models directory
CLIENT_MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "client-models")
