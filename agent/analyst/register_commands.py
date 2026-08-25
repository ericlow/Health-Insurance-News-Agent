"""Register the /analysis slash command with Discord (AGE-94).

Run once, and again whenever the command definition changes. Guild registration
is instant; global registration takes up to ~1 hour to propagate.

Usage:
    export DISCORD_APPLICATION_ID=...   # from Developer Portal
    export DISCORD_BOT_TOKEN=...        # from Developer Portal > Bot
    export DISCORD_GUILD_ID=...         # right-click your server > Copy Server ID
    python3 -m agent.a2.register_commands
"""
import os

import requests

STRING_OPTION = 3

COMMAND = {
    "name": "analysis",
    "description": "Analyze URL(s) and/or a question for impact on Anthem",
    "options": [
        {
            "type": STRING_OPTION,
            "name": "input",
            "description": "URL(s) and/or your question — or a conversation ID + follow-up",
            "required": True,
        }
    ],
}


def register():
    app_id = os.environ["DISCORD_APPLICATION_ID"]
    token = os.environ["DISCORD_BOT_TOKEN"]
    guild_id = os.environ.get("DISCORD_GUILD_ID")

    if guild_id:
        url = f"https://discord.com/api/v10/applications/{app_id}/guilds/{guild_id}/commands"
        scope = f"guild {guild_id}"
    else:
        url = f"https://discord.com/api/v10/applications/{app_id}/commands"
        scope = "global (~1h to propagate)"

    resp = requests.post(url, headers={"Authorization": f"Bot {token}"}, json=COMMAND, timeout=10)
    resp.raise_for_status()
    print(f"Registered /analysis to {scope}: {resp.status_code}")


if __name__ == "__main__":
    register()
