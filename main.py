import discord
from discord import app_commands
from discord.ext import tasks, commands
import datetime
import pytz
import random
import os
from aiohttp import web

# --- MINIMALIST EMBEDDED ASYNC SERVER ROUTING ---
async def home_route(request):
    return web.Response(text="Leeds Assistant Bot is fully operational!")

# --- BOT INTERFACE CONFIGURATIONS ---
TOKEN = os.environ.get('DISCORD_TOKEN')
ALERT_CHANNEL_ID = 1505124887189000214  # Daily reminders channel
STRIKE_CHANNEL_ID = 1505179437585666169  # Strike log channel
GUILD_ID = 1505104807382220870         # Server ID

# Permanent TikTok Database Pool
TIKTOK_BANK = [
    "https://tikwm.com",
    "https://tikwm.com"
]

queued_morning_video = None

SCHEDULE = [
    ('weekday', "08:00", "# @everyone ACTIVITY CHECK"),
    ('weekday', "16:00", "# @everyone REMINDER"),
    ('weekday', "18:00", "# @everyone REMINDER"),
    ('weekday', "20:00", "# @everyone REMINDER"),
    ('weekday', "22:00", "# @everyone FINAL REMINDER"),
    ('weekend', "10:00", "# @everyone ACTIVITY CHECK"),
    ('weekend', "12:00", "# @everyone REMINDER"),
    ('weekend', "13:00", "# @everyone REMINDER"),
    ('weekend', "15:00", "# @everyone REMINDER"),
    ('weekend', "17:00", "# @everyone REMINDER"),
    ('weekend', "20:00", "# @everyone REMINDER"),
    ('weekend', "22:00", "# @everyone FINAL REMINDER")
]

# --- UNIFIED BOT AND SLASH INTERACTION LOGIC ---
class LeedsBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        """Launches the embedded web app server inside the bot's engine loop."""
        # 1. Hard-syncs your slash commands instantly right to your server
        guild_target = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild_target)
        await self.tree.sync(guild=guild_target)
        print("Slash commands synced successfully!")

        # 2. Starts the async web server on the correct port to clear Render's error check
        server_app = web.Application()
        server_app.router.add_get('/', home_route)
        server_runner = web.AppRunner(server_app)
        await server_runner.setup()
        
        assigned_port = int(os.environ.get("PORT", 8080))
        server_site = web.TCPSite(server_runner, '0.0.0.0', assigned_port)
        await server_site.start()
        print(f"Async port listener bound cleanly on port {assigned_port}")

bot = LeedsBot()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    if not scheduler_loop.is_running():
        scheduler_loop.start()

# --- ADMIN PERMISSION MATRIX ---
def is_authorized_staff(member: discord.Member) -> bool:
    if member.guild.owner_id == member.id:
        return True
    staff_roles = {"founder", "co founder", "admin"}
    for role in member.roles:
        if role.name.lower() in staff_roles:
            return True
    return False

def is_high_rank(member: discord.Member) -> bool:
    if member.guild.owner_id == member.id:
        return True
    high_roles = {"founder", "co founder"}
    for role in member.roles:
        if role.name.lower() in high_roles:
            return True
    return False

def clean_tiktok_url(url: str) -> str:
    clean_url = url.strip()
    if "tikwm.com" in clean_url:
        return clean_url
    if "tiktok.com" in clean_url:
        return clean_url.replace("tiktok.com", "tikwm.com")
    return clean_url

def get_strike_message(member: discord.Member, number: int) -> str:
    if number == 1:
        return f"{member.mention} THATS STRIKE ONE REMEMBER 5 IS BAN"
    elif number == 2:
        return f"{member.mention} BREAKING RULES 2ND STRIKE TIMEOUT FOR 30MINS"
    elif number == 3:
        return f"{member.mention} BREAKING RULES 3RD STRIKE TIMEOUT FOR 1HOUR AND 30 MINS"
    elif number == 4:
        return f"{member.mention} BREAKING RULES 4TH STRIKE TIMEOUT FOR 3DAYS"
    elif number == 5:
        return f"{member.mention} YOU BROKE THE RULES TO MANY TIMES YOU ARE BANNED"
    return ""

# --- APPLICATION SLASH COMMAND MAPS ---

@bot.tree.command(name="schedule", description="Displays the automated messaging timetable.")
async def show_schedule(interaction: discord.Interaction):
    schedule_text = (
        "📅 **Automated Alert Timetable (UK Time)** 📅\n\n"
        "**Weekdays (Monday - Friday):**\n"
        "• 08:00 ➔ # ACTIVITY CHECK (With Video)\n"
        "• 16:00 ➔ # REMINDER\n"
        "• 18:00 ➔ # REMINDER\n"
        "• 20:00 ➔ # REMINDER\n"
        "• 22:00 ➔ # FINAL REMINDER\n\n"
        "**Weekends (Saturday - Sunday):**\n"
        "• 10:00 ➔ # ACTIVITY CHECK (With Video)\n"
        "• 12:00 ➔ # REMINDER\n"
        "• 13:00 ➔ # REMINDER\n"
        "• 15:00 ➔ # REMINDER\n"
        "• 17:00 ➔ # REMINDER\n"
        "• 20:00 ➔ # REMINDER\n"
        "• 22:00 ➔ # FINAL REMINDER"
    )
    await interaction.response.send_message(schedule_text, ephemeral=True)

@bot.tree.command(name="addvideo", description="Queues a specific TikTok video URL for the very next morning alert.")
@app_commands.describe(url="The full TikTok link to send tomorrow morning")
async def add_morning_video(interaction: discord.Interaction, url: str):
    if not is_authorized_staff(interaction.user):
        await interaction.response.send_message("❌ Access Denied: Only Founders, co founders, and Admins can use this.", ephemeral=True)
        return

    if "tiktok.com" not in url.lower():
        await interaction.response.send_message("❌ Error: Please provide a valid TikTok URL link.", ephemeral=True)
        return
        
    global queued_morning_video
    queued_morning_video = clean_tiktok_url(url)
    await interaction.response.send_message(f"🔊 Video URL Processed for next morning: {queued_morning_video}", ephemeral=True)

@bot.tree.command(name="strike", description="Issue a REAL strike to a member (1-5) and apply punishment inside the strike channel.")
@app_commands.describe(member="The user to strike", number="The strike level (1 to 5)")
@app_commands.choices(number=[
    app_commands.Choice(name="Strike 1: Warning", value=1),
    app_commands.Choice(name="Strike 2: 30 Min Timeout", value=2),
    app_commands.Choice(name="Strike 3: 1.5 Hour Timeout", value=3),
    app_commands.Choice(name="Strike 4: 3 Day Timeout", value=4),
    app_commands.Choice(name="Strike 5: Permanent Ban", value=5)
])
async def issue_strike(interaction: discord.Interaction, member: discord.Member, number: int):
    if not is_authorized_staff(interaction.user):
        await interaction.response.send_message("❌ Access Denied.", ephemeral=True)
        return

    if is_high_rank(member) and interaction.guild.owner_id != interaction.user.id:
        await interaction.response.send_message("❌ Protection Block: Founders and co founders cannot be real-striked by staff.", ephemeral=True)
        return

    if interaction.user.top_role <= member.top_role and interaction.guild.owner_id != interaction.user.id:
        await interaction.response.send_message("❌ Hierarchy Block: You cannot strike a higher or equal role ranking.", ephemeral=True)
        return

    strike_channel = bot.get_channel(STRIKE_CHANNEL_ID)
    if not strike_channel:
        await interaction.response.send_message("❌ Channel configuration error.", ephemeral=True)
        return

    msg = get_strike_message(member, number)

    try:
        if number == 1:
            await strike_channel.send(msg)
        elif number == 2:
            await member.timeout(datetime.timedelta(minutes=30), reason="Strike 2")
            await strike_channel.send(msg)
        elif number == 3:
            await member.timeout(datetime.timedelta(hours=1, minutes=30), reason="Strike 3")
            await strike_channel.send(msg)
        elif number == 4:
            await member.timeout(datetime.timedelta(days=3), reason="Strike 4")
            await strike_channel.send(msg)
        elif number == 5:
            await member.ban(reason="Strike 5", delete_message_days=1)
            await strike_channel.send(msg)

        await interaction.response.send_message(f"✅ Real Strike {number} sent to {strike_channel.mention}.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

@bot.tree.command(name="teststrike", description="Simulate a fake strike warning message that drops in channel but does not punish.")
@app_commands.describe(member="The user to simulate onto", number="The strike level to fake (1 to 5)")
@app_commands.choices(number=[
    app_commands.Choice(name="Fake Strike 1: Warning", value=1),
    app_commands.Choice(name="Fake Strike 2: 30 Min Timeout", value=2),
    app_commands.Choice(name="Fake Strike 3: 1.5 Hour Timeout", value=3),
    app_commands.Choice(name="Fake Strike 4: 3 Day Timeout", value=4),
    app_commands.Choice(name="Fake Strike 5: Permanent Ban", value=5)
])
async def test_strike(interaction: discord.Interaction, member: discord.Member, number: int):
    if not is_authorized_staff(interaction.user):
        await interaction.response.send_message("❌ Access Denied.", ephemeral=True)
        return

    strike_channel = bot.get_channel(STRIKE_CHANNEL_ID)
    if not strike_channel:
        await interaction.response.send_message("❌ Channel error.", ephemeral=True)
        return

    base_msg = get_strike_message(member, number)
    fake_msg = f"{base_msg} (TEST BY {interaction.user.mention})"
    
    await strike_channel.send(fake_msg)
    await interaction.response.send_message(f"👻 Test Strike dropped in {strike_channel.mention}.", ephemeral=True)

# --- TRACKING TIMER CLOCK TASK ENGINE ---
@tasks.loop(minutes=1)
async def scheduler_loop():
    global queued_morning_video
    await bot.wait_until_ready()
    
    tz = pytz.timezone('Europe/London')
    now = datetime.datetime.now(tz)
    
    current_time = now.strftime("%H:%M")
