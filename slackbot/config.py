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
GITHUB_REPO = os.environ.get("GITHUB_REPO", "")

# Devin API
DEVIN_API_KEY = os.environ.get("DEVIN_API_KEY", "")

# Sample app
SAMPLE_APP_URL = os.environ.get("SAMPLE_APP_URL", "http://localhost:3000")

# Client models directory
CLIENT_MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "client-models")
