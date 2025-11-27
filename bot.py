"""
MatchBot: Discord bot for NTU–Tsinghua alumni profiles and keyword-based matching.

Core features (MVP):
- Create profile (via DM)
- Update profile (via DM)
- Search profiles by keyword in #search-user
"""

import os
import asyncio
from typing import Optional

import discord
from discord import Embed
from dotenv import load_dotenv

from db import Database

# ---------------------------------------------------------------------------
# Config / setup
# ---------------------------------------------------------------------------

# Load Discord token from .env
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise SystemExit("DISCORD_TOKEN not set in environment")

# Discord intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Channel where search is allowed
SEARCH_CHANNEL_NAME = "search-user"

# Global client + database
client = discord.Client(intents=intents)
db = Database("profiles.db")


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def is_mention_command(
    message: discord.Message,
    bot_user_id: int,
) -> Optional[str]:
    """
    If the message starts with a mention of the bot, return the rest of the text
    (command + args). Otherwise return None.

    Examples:
        "<@1234> create-profile"
        "<@!1234> search ai"
    """
    content = message.content.strip()
    lead1 = f"<@{bot_user_id}>"
    lead2 = f"<@!{bot_user_id}>"

    if content.startswith(lead1):
        return content[len(lead1):].strip()
    if content.startswith(lead2):
        return content[len(lead2):].strip()
    return None


async def prompt_user(
    user: discord.User | discord.Member,
    question: str,
    timeout: int = 120,
) -> Optional[str]:
    """
    Ask the user a question in DM and wait for a reply.

    Returns:
        - stripped message content if the user replied in time
        - None if it timed out
    """
    try:
        dm = user.dm_channel
        if dm is None:
            dm = await user.create_dm()

        await dm.send(question)

        def check(m: discord.Message) -> bool:
            return (
                m.author.id == user.id
                and isinstance(m.channel, discord.DMChannel)
            )

        msg = await client.wait_for("message", check=check, timeout=timeout)
        return msg.content.strip()
    except asyncio.TimeoutError:
        return None


# ---------------------------------------------------------------------------
# Discord event handlers
# ---------------------------------------------------------------------------

@client.event
async def on_ready() -> None:
    print(f"Logged in as {client.user} (ID: {client.user.id})")
    print("------")


@client.event
async def on_message(message: discord.Message) -> None:
    # Ignore messages from bots (including ourselves)
    if message.author.bot:
        return

    # Only respond to messages that start with a mention of the bot
    cmd_text = is_mention_command(message, client.user.id)
    if cmd_text is None:
        return

    parts = cmd_text.split()
    if not parts:
        return

    cmd = parts[0].lower()
    args = parts[1:]

    # -------------------------------------------------------------------
    # CREATE PROFILE
    # -------------------------------------------------------------------
    if cmd == "create-profile":
        await message.channel.send(
            f"{message.author.mention} I sent you a DM to create your profile."
        )

        user = message.author

        name_role = await prompt_user(
            user,
            'Please provide your Name / Role (e.g., "Alice — AI founder"):',
        )
        if name_role is None:
            await user.send("Timed out. Profile creation cancelled.")
            return

        description = await prompt_user(
            user, "Short description (one or two sentences):"
        )
        if description is None:
            await user.send("Timed out. Profile creation cancelled.")
            return

        keywords = await prompt_user(
            user,
            "Keywords — comma separated (e.g., investor, AI founder, cybersecurity):",
        )
        if keywords is None:
            await user.send("Timed out. Profile creation cancelled.")
            return

        keywords_norm = ",".join(
            [k.strip().lower() for k in keywords.split(",") if k.strip()]
        )

        # For now, we store name_role as both name and role for simplicity.
        db.upsert_profile(
            user_id=str(user.id),
            name=name_role,
            role=name_role,
            description=description,
            keywords=keywords_norm,
        )

        await user.send(
            "✅ Profile saved. You can update it with `@MatchBot update-profile`."
        )

    # -------------------------------------------------------------------
    # UPDATE PROFILE
    # -------------------------------------------------------------------
    elif cmd == "update-profile":
        await message.channel.send(
            f"{message.author.mention} I sent you a DM to update your profile."
        )

        user = message.author
        profile = db.get_profile(str(user.id))
        if not profile:
            await user.send(
                "No existing profile found. Use `@MatchBot create-profile` to create one."
            )
            return

        name_role = profile["name"]
        description = profile["description"]
        keywords = profile["keywords"]

        await user.send(
            "Current profile shown below. "
            "Reply with a new value, or send an empty message to keep the existing value."
        )
        await user.send(
            f"Name/Role: {name_role}\n"
            f"Description: {description}\n"
            f"Keywords: {keywords}"
        )

        new_name = await prompt_user(
            user, "New Name/Role (or leave empty to keep):"
        )
        if new_name is None:
            await user.send("Timed out. Update cancelled.")
            return
        if new_name == "":
            new_name = name_role

        new_desc = await prompt_user(
            user, "New Description (or leave empty to keep):"
        )
        if new_desc is None:
            await user.send("Timed out. Update cancelled.")
            return
        if new_desc == "":
            new_desc = description

        new_keywords = await prompt_user(
            user,
            "New Keywords — comma separated (or leave empty to keep):",
        )
        if new_keywords is None:
            await user.send("Timed out. Update cancelled.")
            return
        if new_keywords == "":
            new_keywords_norm = keywords
        else:
            new_keywords_norm = ",".join(
                [k.strip().lower() for k in new_keywords.split(",") if k.strip()]
            )

        db.upsert_profile(
            user_id=str(user.id),
            name=new_name,
            role=new_name,
            description=new_desc,
            keywords=new_keywords_norm,
        )

        await user.send("✅ Profile updated.")

    # -------------------------------------------------------------------
    # SEARCH PROFILES
    # -------------------------------------------------------------------
    elif cmd == "search":
        # Only allow in dedicated search channel
        if getattr(message.channel, "name", None) != SEARCH_CHANNEL_NAME:
            await message.channel.send(
                f"Please run searches in the `#{SEARCH_CHANNEL_NAME}` channel."
            )
            return

        if not args:
            await message.channel.send(
                "Usage: `@MatchBot search <keyword>`"
            )
            return

        keyword = " ".join(args).strip().lower()
        results = db.search(keyword)

        if not results:
            await message.channel.send(
                f'No profiles found matching "{keyword}".'
            )
            return

        embed = Embed(
            title=f'Search results for "{keyword}"',
            color=0x2ECC71,
        )

        for r in results:
            user_id = r["user_id"]
            display = r["name"] or f"<@{user_id}>"
            desc = r["description"] or ""
            matched = r["matched_keywords"]
            mention = f"<@{user_id}>"

            embed.add_field(
                name=f"{display} — {mention}",
                value=f"{desc}\nMatched keywords: {matched}",
                inline=False,
            )

        await message.channel.send(embed=embed)

    # -------------------------------------------------------------------
    # UNKNOWN COMMAND
    # -------------------------------------------------------------------
    else:
        await message.channel.send(
            "Unknown command. Supported commands: "
            "`create-profile`, `update-profile`, `search`."
        )


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    client.run(TOKEN)
