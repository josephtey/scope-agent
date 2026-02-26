"""
Scope Agent — Slack Bot

Main application that ties together:
- Scoping Agent (LLM-powered conversation)
- Prototype Generator (visual variants)
- GitHub Issue Creator (final handoff)
- Client Model (persistent knowledge)

Runs as a Slack Bolt app in Socket Mode.
"""

import json
import os
import tempfile
import threading
from typing import Optional

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

import config
import scoping_agent
import prototype_generator
import devin_integration
import github_issue
import client_model

# Initialize Slack app
app = App(
    token=config.SLACK_BOT_TOKEN,
    signing_secret=config.SLACK_SIGNING_SECRET,
)

# In-memory conversation state per channel/thread
# Key: (channel_id, thread_ts) -> conversation state
conversations: dict[tuple[str, str], dict] = {}


def _get_convo_key(channel: str, thread_ts: Optional[str], ts: str) -> tuple[str, str]:
    """Get the conversation key. Use thread_ts if in a thread, else the message ts."""
    return (channel, thread_ts or ts)


def _get_or_create_convo(key: tuple[str, str], client_id: str) -> dict:
    """Get or create a conversation state."""
    if key not in conversations:
        conversations[key] = {
            "client_id": client_id,
            "history": [],
            "phase": "scoping",  # scoping -> prototyping -> confirming -> submitted
            "prototype_round": 0,
            "selected_variant": None,
            "feature_spec": None,
        }
    return conversations[key]


def _derive_client_id(channel_name: str) -> str:
    """
    Derive a client ID from the Slack channel name.
    In production, you'd map channels to clients in a database.
    Convention: channel named #acme-requests -> client_id = "acme"
    """
    name = channel_name.lower().replace("-requests", "").replace("-support", "")
    return name


@app.event("app_mention")
def handle_mention(event, say, client):
    """Handle @agent mentions in client channels."""
    channel = event["channel"]
    user = event["user"]
    text = event.get("text", "").strip()
    ts = event["ts"]
    thread_ts = event.get("thread_ts")

    # Remove the bot mention from the text
    # Format is like "<@U1234> message text"
    if text.startswith("<@"):
        close_bracket = text.find(">")
        if close_bracket != -1:
            text = text[close_bracket + 1:].strip()

    if not text:
        say(
            text="Hey! I'm your feature scoping assistant. Tell me what you'd like to customize about the dashboard and I'll help you scope it out.",
            thread_ts=thread_ts or ts,
        )
        return

    # Get channel info for client ID derivation
    try:
        channel_info = client.conversations_info(channel=channel)
        channel_name = channel_info["channel"]["name"]
    except Exception:
        channel_name = channel

    client_id = _derive_client_id(channel_name)
    convo_key = _get_convo_key(channel, thread_ts, ts)
    convo = _get_or_create_convo(convo_key, client_id)

    # Route based on conversation phase
    if convo["phase"] == "scoping":
        _handle_scoping(convo, convo_key, text, say, client, channel, thread_ts or ts)
    elif convo["phase"] == "prototyping":
        _handle_prototype_feedback(convo, convo_key, text, say, client, channel, thread_ts or ts)
    elif convo["phase"] == "confirming":
        _handle_confirmation(convo, convo_key, text, say, client, channel, thread_ts or ts)
    elif convo["phase"] == "submitted":
        say(
            text="This request has already been submitted! Start a new thread for a new feature request.",
            thread_ts=thread_ts or ts,
        )


@app.event("message")
def handle_message(event, say, client):
    """Handle direct messages in threads (no @mention needed after first message)."""
    # Only process threaded replies
    thread_ts = event.get("thread_ts")
    if not thread_ts:
        return

    # Skip bot messages
    if event.get("bot_id") or event.get("subtype") == "bot_message":
        return

    channel = event["channel"]
    text = event.get("text", "").strip()
    ts = event["ts"]

    convo_key = _get_convo_key(channel, thread_ts, ts)

    # Only respond if we have an active conversation in this thread
    if convo_key not in conversations:
        return

    convo = conversations[convo_key]

    # Get channel info
    try:
        channel_info = client.conversations_info(channel=channel)
        channel_name = channel_info["channel"]["name"]
    except Exception:
        channel_name = channel

    # Route based on phase
    if convo["phase"] == "scoping":
        _handle_scoping(convo, convo_key, text, say, client, channel, thread_ts)
    elif convo["phase"] == "prototyping":
        _handle_prototype_feedback(convo, convo_key, text, say, client, channel, thread_ts)
    elif convo["phase"] == "confirming":
        _handle_confirmation(convo, convo_key, text, say, client, channel, thread_ts)


def _handle_scoping(convo, convo_key, text, say, slack_client, channel, thread_ts):
    """Handle messages during the scoping phase."""
    client_id = convo["client_id"]

    # Get agent response
    response = scoping_agent.get_response(
        client_id=client_id,
        conversation_history=convo["history"],
        user_message=text,
    )

    # Update conversation history
    convo["history"].append({"role": "user", "content": text})
    convo["history"].append({"role": "assistant", "content": response})

    # Check if ready to prototype
    if scoping_agent.is_ready_to_prototype(response):
        # Clean the marker from the displayed response
        display_response = response.replace("[READY_TO_PROTOTYPE]", "").strip()
        say(text=display_response, thread_ts=thread_ts)

        convo["phase"] = "prototyping"
        _generate_and_send_prototypes(convo, say, slack_client, channel, thread_ts)
        return

    # Check if ready to submit (can happen in one step for simple requests)
    if scoping_agent.is_ready_to_submit(response):
        _handle_submit(convo, response, say, slack_client, channel, thread_ts)
        return

    # Regular scoping response
    say(text=response, thread_ts=thread_ts)


def _generate_and_send_prototypes(convo, say, slack_client, channel, thread_ts):
    """Generate 3 prototype variants and post to the thread.

    Uses Devin API if configured (creates real PRs on sample-client-project),
    otherwise falls back to local Playwright screenshots.
    """
    convo["prototype_round"] += 1
    client_id = convo["client_id"]

    # Build a feature description from conversation history
    feature_description = _extract_feature_description(convo)

    say(
        text=":art: Great — I'm going to prototype a few versions for you. Be right back!",
        thread_ts=thread_ts,
    )

    def _generate():
        try:
            result = prototype_generator.generate_prototypes(
                feature_description=feature_description,
                client_id=client_id,
            )

            mode = result["mode"]
            variants = result["variants"]
            convo["prototype_results"] = result  # Store for later reference

            print(f"[_generate] mode={mode}, num_variants={len(variants)}")
            for variant in variants:
                print(f"[_generate] Sending variant: {variant.get('name')}, success={variant.get('success')}, screenshots={variant.get('screenshot_urls', [])}")
                if mode == "devin":
                    _send_devin_variant(variant, slack_client, channel, thread_ts)
                else:
                    _send_local_variant(variant, slack_client, channel, thread_ts)

            slack_client.chat_postMessage(
                channel=channel,
                text=(
                    "Here are a few ideas! Which direction feels right to you?\n"
                    "You can pick one, mix and match parts you like, or tell me what to change."
                ),
                thread_ts=thread_ts,
            )
        except Exception as e:
            print(f"[_generate] ERROR: {e}")
            import traceback
            traceback.print_exc()
            slack_client.chat_postMessage(
                channel=channel,
                text=":warning: Sorry, something went wrong generating the prototypes. Let me try again.",
                thread_ts=thread_ts,
            )

    thread = threading.Thread(target=_generate)
    thread.start()


def _extract_feature_description(convo: dict) -> str:
    """Extract a feature description from the conversation history."""
    user_msgs = [m["content"] for m in convo["history"] if m["role"] == "user"]
    assistant_msgs = [m["content"] for m in convo["history"] if m["role"] == "assistant"]
    if user_msgs:
        return " | ".join(user_msgs[-3:])  # Last 3 user messages as context
    return "Feature customization request"


def _send_devin_variant(variant: dict, slack_client, channel: str, thread_ts: str):
    """Send a Devin-generated variant screenshot to Slack."""
    import tempfile
    import requests as req

    name = variant.get("name", "Variant")
    description = variant.get("description", "")
    screenshot_urls = variant.get("screenshot_urls", [])
    success = variant.get("success", False)

    print(f"[send_devin_variant] name={name}, success={success}, screenshot_urls={screenshot_urls}")

    if not success:
        slack_client.chat_postMessage(
            channel=channel,
            text=f"*{name}*\n{description}\n:warning: _This variant didn't finish generating._",
            thread_ts=thread_ts,
        )
        return

    # Try to download and upload the screenshot to Slack
    # Devin attachment URLs must go through api.devin.ai/v1/attachments/ (requires Bearer auth)
    auth_headers = {"Authorization": f"Bearer {config.DEVIN_API_KEY}"}

    if screenshot_urls:
        for url in screenshot_urls:
            try:
                # Rewrite app.devin.ai/attachments/ → api.devin.ai/v1/attachments/
                download_url = url.replace(
                    "https://app.devin.ai/attachments/",
                    "https://api.devin.ai/v1/attachments/",
                )
                print(f"[send_devin_variant] Downloading screenshot: {download_url}")
                resp = req.get(download_url, headers=auth_headers, timeout=30, allow_redirects=True)
                print(f"[send_devin_variant] Download status: {resp.status_code}, size: {len(resp.content)}")
                if resp.status_code == 200 and len(resp.content) > 100:
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                        f.write(resp.content)
                        tmp_path = f.name

                    slack_client.files_upload_v2(
                        channel=channel,
                        file=tmp_path,
                        filename=f"prototype_{variant.get('key', 'x').lower()}.png",
                        title=name,
                        initial_comment=f"*{name}*\n{description}",
                        thread_ts=thread_ts,
                    )
                    print(f"[send_devin_variant] Uploaded screenshot to Slack for {name}")
                    return
                else:
                    print(f"[send_devin_variant] Bad response: status={resp.status_code}")
            except Exception as e:
                print(f"[send_devin_variant] Failed to download/upload screenshot: {e}")
                import traceback
                traceback.print_exc()

    # Fallback: just post the text description
    print(f"[send_devin_variant] Falling back to text for {name}")
    slack_client.chat_postMessage(
        channel=channel,
        text=f"*{name}*\n{description}",
        thread_ts=thread_ts,
    )


def _send_local_variant(variant: dict, slack_client, channel: str, thread_ts: str):
    """Send a locally-generated variant screenshot to Slack."""
    name = variant.get("name", "Variant")
    description = variant.get("description", "")
    path = variant.get("screenshot_path", "")

    if path and path.endswith(".png"):
        try:
            slack_client.files_upload_v2(
                channel=channel,
                file=path,
                filename=f"prototype_{variant.get('key', 'x').lower()}.png",
                title=name,
                initial_comment=f"*{name}*\n{description}",
                thread_ts=thread_ts,
            )
            return
        except Exception:
            pass

    slack_client.chat_postMessage(
        channel=channel,
        text=f"*{name}*\n{description}",
        thread_ts=thread_ts,
    )


def _handle_prototype_feedback(convo, convo_key, text, say, slack_client, channel, thread_ts):
    """Handle client feedback on prototypes."""
    client_id = convo["client_id"]

    # Build variant context from whatever was generated (Devin or local)
    proto_results = convo.get("prototype_results", {})
    variants_list = proto_results.get("variants", prototype_generator.get_variant_descriptions())
    variant_context = "\n".join(
        f"- {v.get('name', 'Variant')}: {v.get('description', '')}" for v in variants_list
    )
    mode = proto_results.get("mode", "local")
    context_msg = (
        f"The client was shown these 3 prototype variants:\n{variant_context}\n\n"
        f"The client's feedback is: {text}"
    )

    response = scoping_agent.get_response(
        client_id=client_id,
        conversation_history=convo["history"],
        user_message=context_msg,
    )

    convo["history"].append({"role": "user", "content": text})
    convo["history"].append({"role": "assistant", "content": response})

    if scoping_agent.is_ready_to_submit(response):
        _handle_submit(convo, response, say, slack_client, channel, thread_ts)
        return

    # Check if they want another prototype round
    if scoping_agent.is_ready_to_prototype(response):
        display_response = response.replace("[READY_TO_PROTOTYPE]", "").strip()
        say(text=display_response, thread_ts=thread_ts)
        _generate_and_send_prototypes(convo, say, slack_client, channel, thread_ts)
        return

    say(text=response, thread_ts=thread_ts)


def _handle_confirmation(convo, convo_key, text, say, slack_client, channel, thread_ts):
    """Handle final confirmation before submission."""
    text_lower = text.lower()
    if any(word in text_lower for word in ["yes", "confirm", "submit", "send", "approve", "looks good", "lgtm"]):
        _submit_issue(convo, say, slack_client, channel, thread_ts)
    else:
        # Go back to scoping
        convo["phase"] = "scoping"
        _handle_scoping(convo, convo_key, text, say, slack_client, channel, thread_ts)


def _handle_submit(convo, response, say, slack_client, channel, thread_ts):
    """Extract the spec and ask for final confirmation."""
    display_response = response.replace("[READY_TO_SUBMIT]", "").strip()

    # Extract the feature spec
    spec = scoping_agent.extract_feature_spec(response)
    if spec:
        convo["feature_spec"] = spec
        convo["phase"] = "confirming"

        say(text=display_response, thread_ts=thread_ts)
        say(
            text=(
                ":clipboard: *Ready to submit this to the engineering team.*\n"
                "Reply 'confirm' to create the GitHub issue, or tell me what to change."
            ),
            thread_ts=thread_ts,
        )
    else:
        say(
            text="I tried to generate the final spec but something went wrong. Let me try again — could you summarize what you'd like one more time?",
            thread_ts=thread_ts,
        )
        convo["phase"] = "scoping"


def _submit_issue(convo, say, slack_client, channel, thread_ts):
    """Create the GitHub issue and update the client model."""
    spec = convo.get("feature_spec")
    if not spec:
        say(
            text="Something went wrong — I don't have a feature spec to submit. Let's try again.",
            thread_ts=thread_ts,
        )
        convo["phase"] = "scoping"
        return

    client_id = convo["client_id"]
    variant = convo.get("selected_variant", "Client-refined variant")

    # Build conversation summary
    user_messages = [m["content"] for m in convo["history"] if m["role"] == "user"]
    conversation_summary = (
        f"**Scoping conversation ({len(user_messages)} exchanges):**\n\n"
        + "\n".join(f"> {msg}" for msg in user_messages[:10])
    )

    say(
        text=":rocket: Creating GitHub issue...",
        thread_ts=thread_ts,
    )

    # Create the issue
    result = github_issue.create_issue(
        feature_spec=spec,
        client_id=client_id,
        conversation_summary=conversation_summary,
        prototype_choice=variant,
    )

    if result and result.startswith("http"):
        say(
            text=f":white_check_mark: *Issue created!*\n{result}\n\nThe engineering team will take it from here. I've saved your preferences for next time.",
            thread_ts=thread_ts,
        )
    else:
        # Demo mode: show the formatted issue
        say(
            text=f":white_check_mark: *Feature request captured!*\n\n```{result[:2000]}```\n\n_In production, this would be a GitHub issue. Your preferences have been saved for next time._",
            thread_ts=thread_ts,
        )

    # Update client model with preferences from this conversation
    if spec.get("client_preferences"):
        for pref in spec["client_preferences"]:
            client_model.add_preference(client_id, "preferred_patterns", pref)

    client_model.add_request(client_id, {
        "title": spec.get("title", "Untitled"),
        "status": "submitted",
        "complexity": spec.get("complexity_estimate", "unknown"),
        "prototype_choice": variant,
    })

    convo["phase"] = "submitted"


def main():
    """Start the Slack bot."""
    if not config.SLACK_BOT_TOKEN:
        print("=" * 60)
        print("DEMO MODE — No Slack credentials configured.")
        print("To connect to Slack, set these environment variables:")
        print("  SLACK_BOT_TOKEN")
        print("  SLACK_SIGNING_SECRET")
        print("  SLACK_APP_TOKEN (for Socket Mode)")
        print("")
        print("See .env.example for all configuration options.")
        print("=" * 60)
        print("\nRunning conversation demo instead...\n")
        _run_demo()
        return

    print("Starting Scope Agent Slack bot...")
    handler = SocketModeHandler(app, config.SLACK_APP_TOKEN)
    handler.start()


def _run_demo():
    """Run an interactive demo in the terminal when Slack isn't configured."""
    print("=" * 60)
    print("SCOPE AGENT — Interactive Demo")
    print("=" * 60)

    # Show mode info
    if devin_integration.is_configured():
        print("\nMODE: Devin API (real prototype generation)")
        conn = devin_integration.test_connection()
        if conn["ok"]:
            print("Devin API: Connected")
        else:
            print(f"Devin API: Connection issue — {conn.get('error', 'unknown')}")
            print("Will fall back to local screenshot generation.")
    else:
        print("\nMODE: Local (Playwright screenshots)")
        print("Set DEVIN_API_KEY to enable real prototype generation.")

    print(f"Target repo: {config.CLIENT_PROJECT_REPO}")
    print(f"GitHub issues: {config.GITHUB_REPO}")
    print("\nYou are a client talking to the scoping agent.")
    print("Try describing a feature you want for your dashboard.")
    print("Type 'quit' to exit.\n")

    client_id = "demo-client"
    client_model.load_model(client_id, "Demo Client")
    history = []

    while True:
        user_input = input("\nYou: ").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            break

        response = scoping_agent.get_response(
            client_id=client_id,
            conversation_history=history,
            user_message=user_input,
        )

        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": response})

        # Clean markers for display
        display = response.replace("[READY_TO_PROTOTYPE]", "").replace("[READY_TO_SUBMIT]", "")
        print(f"\nAgent: {display}")

        if scoping_agent.is_ready_to_prototype(response):
            print("\n--- PROTOTYPE PHASE ---")
            feature_desc = " | ".join(
                m["content"] for m in history if m["role"] == "user"
            )[-500:]

            result = prototype_generator.generate_prototypes(
                feature_description=feature_desc,
                client_id=client_id,
            )

            mode = result["mode"]
            print(f"Mode: {mode}")
            for v in result["variants"]:
                print(f"\n  {v.get('name', 'Variant')}: {v.get('description', '')}")
                if v.get("pr_url"):
                    print(f"  PR: {v['pr_url']}")
                if v.get("session_url"):
                    print(f"  Session: {v['session_url']}")
                if v.get("screenshot_path"):
                    print(f"  File: {v['screenshot_path']}")
            print("\n--- Pick one or give feedback ---")

        if scoping_agent.is_ready_to_submit(response):
            spec = scoping_agent.extract_feature_spec(response)
            if spec:
                print("\n--- FINAL FEATURE SPEC ---")
                print(json.dumps(spec, indent=2))
                print("\n--- Creating GitHub issue... ---")
                result = github_issue.create_issue(
                    feature_spec=spec,
                    client_id=client_id,
                    conversation_summary="Demo conversation",
                )
                print(f"\nResult: {result[:500] if result else 'Failed'}")
                client_model.add_request(client_id, {
                    "title": spec.get("title", ""),
                    "status": "submitted",
                })
                break

    print("\nClient model saved to:", client_model._model_path(client_id))


if __name__ == "__main__":
    main()
