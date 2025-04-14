import discord
from discord.ext import commands
import datetime
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
TARGET_CHANNEL_ID = int(os.getenv("TARGET_CHANNEL_ID"))
ALLOWED_ROLES = os.getenv("ALLOWED_ROLES").split(",")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

def has_any_role(roles):
    def predicate(ctx):
        return any(role.name in roles for role in ctx.author.roles)
    return commands.check(predicate)

@bot.command(name='bklog')
@has_any_role(ALLOWED_ROLES)
async def log_messages(ctx, year: int, month: int, day: int):
    """Fetch messages from a specific day and DM them to the user."""
    try:
        start = datetime.datetime(year, month, day)
        end = start + datetime.timedelta(days=1)
    except ValueError:
        await ctx.send("❌ Invalid date.")
        return

    channel = bot.get_channel(TARGET_CHANNEL_ID)
    if channel is None:
        await ctx.send("❌ Channel not found.")
        return

    log_file = f"channel_log_{year}_{month:02}_{day:02}.txt"
    message_count = 0

    await ctx.send(f"⏳ Collecting messages from {channel.mention} on {year}-{month:02}-{day:02}...")

    with open(log_file, "w", encoding="utf-8") as f:
        async for message in channel.history(after=start, before=end, oldest_first=True):
            mentioned = ', '.join(str(user) for user in message.mentions) or "None"
            f.write(f"[{message.created_at}] Author: {message.author}. Mentioned: {mentioned}.\n")
            message_count += 1

    try:
        await ctx.author.send(
            content=f"📄 Log of {message_count} messages from {channel.mention} on {year}-{month:02}-{day:02}:",
            file=discord.File(log_file)
        )
        await ctx.send("✅ Log sent to your DMs!")
    except discord.Forbidden:
        await ctx.send("❌ Couldn’t send DM. Please enable direct messages from server members.")

    os.remove(log_file)

@bot.event
async def on_ready():
    print(f"✅ Bot is online as {bot.user}")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("🚫 You don’t have permission to use this command.")
    else:
        raise error  # Optional: re-raise unhandled errors


bot.run(TOKEN)
