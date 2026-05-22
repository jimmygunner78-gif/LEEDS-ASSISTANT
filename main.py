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

# Global dictionary managing active timetable messages dynamically
SCHEDULE_DATA = {
    'weekday_08:00': "# @everyone ACTIVITY CHECK",
    'weekday_16:00': "# @everyone REMINDER",
    'weekday_18:00': "# @everyone REMINDER",
    'weekday_20:00': "# @everyone REMINDER",
    'weekday_22:00': "# @everyone FINAL REMINDER",
    'weekend_10:00': "# @everyone ACTIVITY CHECK",
    'weekend_12:00': "# @everyone REMINDER",
    'weekend_13:00': "# @everyone REMINDER",
    'weekend_15:00': "# @everyone REMINDER",
    'weekend_17:00': "# @everyone REMINDER",
    'weekend_20:00': "# @everyone REMINDER",
    'weekend_22:00': "# @everyone FINAL REMINDER"
}

# Ordered structural schedule blueprint
SCHEDULE_KEYS = [
    ('weekday', "08:00", 'weekday_08:00'),
    ('weekday', "16:00", 'weekday_16:00'),
    ('weekday', "18:00", 'weekday_18:00'),
    ('weekday', "20:00", 'weekday_20:00'),
    ('weekday', "22:00", 'weekday_22:00'),
    ('weekend', "10:00", 'weekend_10:00'),
    ('weekend', "12:00", 'weekend_12:00'),
    ('weekend', "13:00", 'weekend_13:00'),
    ('weekend', "15:00", 'weekend_15:00'),
    ('weekend', "17:00", 'weekend_17:00'),
    ('weekend', "20:00", 'weekend_20:00'),
    ('weekend', "22:00", 'weekend_22:00')
]

# --- INSTANT SYNC ENGINE ---
class LeedsBotClient(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        """Forces an instant server sync before the bot fully connects."""
        guild_target = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild_target)
        synced_list = await self.tree.sync(guild=guild_target)
        print(f"Successfully synced {len(synced_list)} slash command(s) instantly.")

bot = LeedsBotClient()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    if not scheduler_loop.is_running():
        scheduler_loop.start()

# --- HELPER LOGIC FOR STAFF & LINK CLEANING ---
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
    """Converts standard TikTok URLs to tikwm proxy formatting to fix mobile players and quiet audio issues."""
    clean_url = url.strip()
    
    # Clean out any old broken link variations first
    if "vxtiktok.com" in clean_url:
        clean_url = clean_url.replace("vxtiktok.com", "tiktok.com")
    if "tnktok.com" in clean_url:
        clean_url = clean_url.replace("tnktok.com", "tiktok.com")
        
    # Route straight to active proxy player
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

# --- SLASH COMMANDS ---

@bot.tree.command(name="schedule", description="Displays the automated messaging timetable.")
async def show_schedule(interaction: discord.Interaction):
    await interaction.response.send_message("🔄 Retrieving schedule...", ephemeral=True)
    
    schedule_text = (
        "📅 **Automated Alert Timetable (UK Time)** 📅\n\n"
        "**Weekdays (Monday - Friday):**\n"
        f"• 08:00 ➔ {SCHEDULE_DATA['weekday_08:00']} (With Video)\n"
        f"• 16:00 ➔ {SCHEDULE_DATA['weekday_16:00']}\n"
        f"• 18:00 ➔ {SCHEDULE_DATA['weekday_18:00']}\n"
        f"• 20:00 ➔ {SCHEDULE_DATA['weekday_20:00']}\n"
        f"• 22:00 ➔ {SCHEDULE_DATA['weekday_22:00']}\n\n"
        "**Weekends (Saturday - Sunday):**\n"
        f"• 10:00 ➔ {SCHEDULE_DATA['weekend_10:00']} (With Video)\n"
        f"• 12:00 ➔ {SCHEDULE_DATA['weekend_12:00']}\n"
        f"• 13:00 ➔ {SCHEDULE_DATA['weekend_13:00']}\n"
        f"• 15:00 ➔ {SCHEDULE_DATA['weekend_15:00']}\n"
        f"• 17:00 ➔ {SCHEDULE_DATA['weekend_17:00']}\n"
        f"• 20:00 ➔ {SCHEDULE_DATA['weekend_20:00']}\n"
        f"• 22:00 ➔ {SCHEDULE_DATA['weekend_22:00']}"
    )
    await interaction.edit_original_response(content=schedule_text)

@bot.tree.command(name="editmessage", description="Edit the text content for any specific scheduled reminder time slot.")
@app_commands.describe(time_slot="The targeted time slot context to update", new_text="The new custom text reminder copy")
@app_commands.choices(time_slot=[
    app_commands.Choice(name="Weekday - 08:00 (Activity)", value="weekday_08:00"),
    app_commands.Choice(name="Weekday - 16:00", value="weekday_16:00"),
    app_commands.Choice(name="Weekday - 18:00", value="weekday_18:00"),
    app_commands.Choice(name="Weekday - 20:00", value="weekday_20:00"),
    app_commands.Choice(name="Weekday - 22:00 (Final)", value="weekday_22:00"),
    app_commands.Choice(name="Weekend - 10:00 (Activity)", value="weekend_10:00"),
    app_commands.Choice(name="Weekend - 12:00", value="weekend_12:00"),
    app_commands.Choice(name="Weekend - 13:00", value="weekend_13:00"),
    app_commands.Choice(name="Weekend - 15:00", value="weekend_15:00"),
    app_commands.Choice(name="Weekend - 17:00", value="weekend_17:00"),
    app_commands.Choice(name="Weekend - 20:00", value="weekend_20:00"),
    app_commands.Choice(name="Weekend - 22:00 (Final)", value="weekend_22:00")
])
async def edit_scheduled_message(interaction: discord.Interaction, time_slot: str, new_text: str):
    await interaction.response.send_message("🔄 Checking authorization arrays...", ephemeral=True)
    
    if not is_authorized_staff(interaction.user):
        await interaction.edit_original_response(content="❌ Access Denied: Only Founders, co founders, and Admins can configure the time schedules.")
        return

    SCHEDULE_DATA[time_slot] = new_text
    clean_slot_title = time_slot.replace("_", " ").title()
    await interaction.edit_original_response(content=f"✅ Timetable Updated! **{clean_slot_title}** has been reprogrammed to send:\n➡️ *{new_text}*")

@bot.tree.command(name="addvideo", description="Queues a specific TikTok video URL for the very next morning alert.")
@app_commands.describe(url="The full TikTok link to send tomorrow morning")
async def add_morning_video(interaction: discord.Interaction, url: str):
    await interaction.response.send_message("🔄 Checking permissions...", ephemeral=True)
    
    if not is_authorized_staff(interaction.user):
        await interaction.edit_original_response(content="❌ Access Denied: Only Founders, co founders, and Admins can add custom morning videos.")
        return

    if "tiktok.com" not in url.lower():
        await interaction.edit_original_response(content="❌ Error: Please provide a valid TikTok URL link.")
        return
        
    queued_morning_video = clean_tiktok_url(url)
    await interaction.edit_original_response(content=f"🔊 Video URL Processed! Audio booster proxy active. Target link: {queued_morning_video}")

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
    await interaction.response.send_message("🔄 Processing strike deployment safely...", ephemeral=True)

    if not is_authorized_staff(interaction.user):
        await interaction.edit_original_response(content="❌ Access Denied: You must be a Founder, co founder, or Admin to execute strikes.")
        return

    if is_high_rank(member) and interaction.guild.owner_id != interaction.user.id:
