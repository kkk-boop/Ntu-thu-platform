# # Ntu-thu-platform MatchBot — simple profile matching Discord bot (MVP)

This small project implements a Discord bot that allows users to create and update a searchable profile, and search for other users by keyword.

Features (MVP):
- `@MatchBot create-profile` — interactive DM flow to create your profile
- `@MatchBot update-profile` — edit your existing profile
- `@MatchBot search <keyword>` — run in `#search-user` to find matching profiles

Storage: SQLite (`profiles.db`) stored next to the bot.

Setup

1. Create a Python virtual environment and activate it (Windows PowerShell):

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Create a `.env` file with your bot token (or set `DISCORD_TOKEN` env var):

```
DISCORD_TOKEN=your_bot_token_here
```

4. Invite the bot to your server with appropriate permissions (message reading/sending, DMs). Ensure the bot has the "Message Content Intent" enabled in the developer portal and `message_content` intent toggled on.

Run

```powershell
python bot.py
```

Usage examples

- `@MatchBot create-profile` (the bot DMs you and asks for Name/Role, Description, Keywords)
- `@MatchBot update-profile` (the bot DMs you showing current values; reply with new or empty to keep)
- In `#search-user` channel: `@MatchBot search investor`

Notes & future improvements

- Replace SQLite with Airtable/Firebase/Postgres for multi-server persistence.
- Add slash commands (interactions) and better UI.
- Add tag filters, LLM-enhanced matching, or recommendation scoring.
