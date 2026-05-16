import discord
from discord import app_commands
from discord.ext import tasks, commands
import datetime
import pytz
import random
from flask import Flask
import threading
import os

# --- WEB SERVER ENGINE FOR RENDER & UPTIMEROBOT ---
app = Flask('')

@app.route('/')
def home():
    return "Leeds Assistant Bot is fully operational!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- BOT CONFIGURATION ---
TOKEN = os.environ.get('DISCORD_TOKEN')
ALERT_CHANNEL_ID = 1505124887189000214  # Channel for your daily TikTok reminders
STRIKE_CHANNEL_ID = 1505179437585666169  # Your verified text strike channel ID
GUILD_ID = 1505104807382220870         # Your exact Discord Server ID

# Your permanent database of TikTok links
TIKTOK_BANK = [
    "https://tiktok.com",
    "https://tiktok.com"
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

# --- ADVANCED FORCED SYNC ENGINE構造 ---
class LeedsBotClient(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        """Forces an instant server sync before the bot fully connects."""
        guild_target = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild_target)
        synced_list = await self.tree.sync(guild=guild_target)
        print(f"Successfully synced {len(synced_list)} slash command(s) instantly to the server.")

bot = LeedsBotClient()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    if not scheduler_loop.is_running():
        scheduler_loop.start()

# --- HELPER LOGIC FOR STAFF CHECKING ---
def is_authorized_staff(member: discord.Member) -> bool:
    if member.guild.owner_id == member.id:
        return True
    staff_roles = {"founder", "co-founder", "admin"}
    for role in member.roles:
        if role.name.lower() in staff_roles:
            return True
    return False

def is_high_rank(member: discord.Member) -> bool:
    high_roles = {"founder", "co-founder"}
    for role in member.roles:
        if role.name.lower() in high_roles:
            return True
    return False

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

# --- SLASH COMMANDS ---

@bot.tree.command(name="schedule", description="Displays the automated messaging timetable.")
async def show_schedule(interaction: discord.Interaction):
    schedule_text = (
        "📅 **Automated Alert Timetable (UK Time)** 📅\n\n"
        "**Weekdays (Monday - Friday):**\n"
        "• 08:00 ➔ # ACTIVITY CHECK\n"
        "• 16:00 ➔ # REMINDER\n"
        "• 18:00 ➔ # REMINDER\n"
        "• 20:00 ➔ # REMINDER\n"
        "• 22:00 ➔ # FINAL REMINDER\n\n"
        "**Weekends (Saturday - Sunday):**\n"
        "• 10:00 ➔ # ACTIVITY CHECK\n"
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
        await interaction.response.send_message("❌ Access Denied: Only Founders, Co-Founders, and Admins can add custom morning videos.", ephemeral=True)
        return

    global queued_morning_video
    if "tiktok.com" not in url.lower():
        await interaction.response.send_message("❌ Error: Please provide a valid TikTok URL link.", ephemeral=True)
        return
    queued_morning_video = url
    await interaction.response.send_message(f"✅ Success! The next morning alert will feature this video link: {url}")

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
        await interaction.response.send_message("❌ Access Denied: You must be a Founder, Co-Founder, or Admin to execute strikes.", ephemeral=True)
        return

    if is_high_rank(member) and interaction.guild.owner_id != interaction.user.id:
        await interaction.response.send_message("❌ Protection Block: Founders and Co-Founders cannot be real-striked by staff. Only the Server Owner can execute this.", ephemeral=True)
        return

    if interaction.user.top_role <= member.top_role and interaction.guild.owner_id != interaction.user.id:
        await interaction.response.send_message("❌ Hierarchy Block: You cannot issue a strike to someone with a higher or equal role ranking.", ephemeral=True)
        return

    strike_channel = bot.get_channel(STRIKE_CHANNEL_ID)
    if not strike_channel:
        await interaction.response.send_message("❌ Configuration Error: Could not locate the dedicated strike log channel.", ephemeral=True)
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
            await member.ban(reason="Strike 5: Accumulation Limit Reached", delete_message_days=1)
            await strike_channel.send(msg)

        await interaction.response.send_message(f"✅ Real Strike {number} processed seamlessly in {strike_channel.mention}.", ephemeral=True)

    except discord.Forbidden:
        await interaction.response.send_message("❌ Bot Permission Failure: Ensure the bot role is dragged above the target user in Server Settings.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Execution Failure: {e}", ephemeral=True)

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
        await interaction.response.send_message("❌ Access Denied: You must be a Founder, Co-Founder, or Admin to execute simulation scripts.", ephemeral=True)
        return

    strike_channel = bot.get_channel(STRIKE_CHANNEL_ID)
    if not strike_channel:
        await interaction.response.send_message("❌ Configuration Error: Could not locate the dedicated strike log channel.", ephemeral=True)
        return

    base_msg = get_strike_message(member, number)
    fake_msg = f"{base_msg} (TEST BY {interaction.user.mention})"
    
    await strike_channel.send(fake_msg)
    await interaction.response.send_message(f"👻 Simulation Verified: Fake Test Strike {number} dropped safely in {strike_channel.mention}.", ephemeral=True)

# --- SCHEDULER ENGINE ---

@tasks.loop(minutes=1)
async def scheduler_loop():
    global queued_morning_video
    await bot.wait_until_ready()
    
    tz = pytz.timezone('Europe/London')
    now = datetime.datetime.now(tz)
    
    current_time = now.strftime("%H:%M")
    day_of_week = now.weekday() 
    day_type = 'weekend' if day_of_week >= 5 else 'weekday'
    
    for alert_type, alert_time, alert_msg in SCHEDULE:
        if alert_type == day_type and alert_time == current_time:
            channel = bot.get_channel(ALERT_CHANNEL_ID)
            if channel:
                is_morning = (alert_time == "08:00" and day_type == 'weekday') or (alert_time == "10:00" and day_type == 'weekend')
                
                if is_morning and queued_morning_video is not None:
                    selected_video = queued_morning_video
                    queued_morning_video = None
                else:
                    selected_video = random.choice(TIKTOK_BANK)
                
                await channel.send(f"{alert_msg}\n{selected_video}")
                break

# Run web routing and discord gateway concurrently
threading.Thread(target=run_web_server).start()
bot.run(TOKEN)



