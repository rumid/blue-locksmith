import discord
from discord.ext import commands, tasks
import datetime
import json
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
LOG_SOURCE_CHANNEL_ID = int(os.getenv("LOG_SOURCE_CHANNEL_ID"))
SYNC_SOURCE_CHANNEL_ID = int(os.getenv("SYNC_SOURCE_CHANNEL_ID"))
SYNC_TARGET_THREAD_ID = int(os.getenv("SYNC_TARGET_THREAD_ID"))
ALLOWED_ROLES = os.getenv("ALLOWED_ROLES").split(",")
MAPPING_FILE = os.getenv("MAPPING_FILE", "message_mapping.json")
MESSAGE_REQUIRED_CONTENT = os.getenv("MESSAGE_REQUIRED_CONTENT")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Load or initialize message mappings
if os.path.exists(MAPPING_FILE):
    with open(MAPPING_FILE, 'r') as f:
        message_mapping = json.load(f)
        message_mapping = {int(k): v for k, v in message_mapping.items()}
else:
    message_mapping = {}
print("Loaded message mappings:", message_mapping)

def save_mappings():
    with open(MAPPING_FILE, 'w') as f:
        json.dump(message_mapping, f)

def has_any_role(roles):
    def predicate(ctx):
        return any(role.name in roles for role in ctx.author.roles)
    return commands.check(predicate)

def get_message_link(message):
    return f"https://discord.com/channels/{message.guild.id}/{message.id}"

def create_synced_message(message):
    return f"{message.content}\n\n### ZGŁOSZENIA: {get_message_link(message)}"

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

    channel = bot.get_channel(SYNC_SOURCE_CHANNEL_ID)
    if channel is None:
        await ctx.send("❌ Channel not found.")
        return

    log_file = f"channel_log_{year}_{month:02}_{day:02}.txt"
    message_count = 0

    await ctx.send(f"⏳ Collecting messages from {channel.mention} on {year}-{month:02}-{day:02}...")

    with open(log_file, "w", encoding="utf-8") as f:
        async for message in channel.history(after=start, before=end, oldest_first=True):
            mentioned = ', '.join(str(user) for user in message.mentions) or "None"
            f.write(f"{message.created_at}, {message.author}, {mentioned}.\n")
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
async def on_message(message):
    if (message.channel.id != SYNC_SOURCE_CHANNEL_ID or 
        message.author.bot or 
        MESSAGE_REQUIRED_CONTENT not in message.content):
        return

    thread = bot.get_channel(SYNC_TARGET_THREAD_ID)
    if thread and isinstance(thread, discord.Thread):
        copied_message = await thread.send(create_synced_message(message))
        message_mapping[message.id] = copied_message.id
        save_mappings()

@bot.event
async def on_message_edit(before, after):
    print(f"Before ID: {before.id}")
    print(f"After ID: {after.id}")
    print(f"Message edited: {before.id} -> {after.id}")
    if before.channel.id != SYNC_SOURCE_CHANNEL_ID or before.author.bot:
        return

    thread = bot.get_channel(SYNC_TARGET_THREAD_ID)
    copied_message_id = message_mapping.get(before.id)

    if copied_message_id and thread and isinstance(thread, discord.Thread):
        try:
            copied_message = await thread.fetch_message(copied_message_id)
            await copied_message.edit(content=create_synced_message(after))
        except discord.NotFound:
            print("Copied message not found, maybe deleted?")


@bot.event
async def on_ready():
    print(f"✅ Bot is online as {bot.user}")

@tasks.loop(minutes=5)  # ⏲️ Runs every 5 minutes
async def resync_messages():
    print("🔄 Starting resync...")

    source_channel = bot.get_channel(SYNC_SOURCE_CHANNEL_ID)
    target_thread = bot.get_channel(SYNC_TARGET_THREAD_ID)

    if not source_channel or not target_thread:
        print("Source or target channel not found!")
        return

    for source_message_id, copied_message_id in message_mapping.items():
        try:
            # Fetch source and copied messages
            source_message = await source_channel.fetch_message(source_message_id)
            copied_message = await target_thread.fetch_message(copied_message_id)

            await copied_message.edit(content=create_synced_message(source_message))
            print(f"✅ Resynced message {source_message.id}")
        except discord.NotFound:
            print(f"⚠️ Message {source_message_id} or {copied_message_id} not found, skipping.")
        except Exception as e:
            print(f"❌ Error resyncing message {source_message_id}: {e}")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("🚫 You don’t have permission to use this command.")
    else:
        raise error  # Optional: re-raise unhandled errors


bot.run(TOKEN)
