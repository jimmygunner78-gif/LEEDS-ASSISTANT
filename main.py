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
CHANNEL_ID = 1505124887189000214  # Your verified text channel ID

# Your permanent database of TikTok links
TIKTOK_BANK = [
    "https://tiktok.com",
    "https://tiktok.com"
]

# Global variable to store the manually queued morning video
queued_morning_video = None

# Automated Schedule Table
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

intents = discord.Intents.default()
# Note: Message Content Intent is no longer strictly required for pure slash commands, 
# but keeping your portal switch enabled is highly recommended.
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    
    # Register slash commands globally across all servers the bot is in
    try:
        synced = await bot.tree.sync()
        print(f"Successfully synced {len(synced)} slash command(s).")
    except Exception as e:
        print(f"Failed to sync slash commands: {e}")
        
    if not scheduler_loop.is_running():
        scheduler_loop.start()

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
    # ephemeral=True means only the user running the command sees this response
    await interaction.response.send_message(schedule_text, ephemeral=True)

@bot.tree.command(name="addvideo", description="Queues a specific TikTok video URL for the very next morning alert.")
@app_commands.describe(url="The full TikTok link to send tomorrow morning")
async def add_morning_video(interaction: discord.Interaction, url: str):
    global queued_morning_video
    
    if "tiktok.com" not in url.lower():
        await interaction.response.send_message("❌ Error: Please provide a valid TikTok URL link.", ephemeral=True)
        return
        
    queued_morning_video = url
    await interaction.response.send_message(f"✅ Success! The next morning alert will feature this video link: {url}")

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
            channel = bot.get_channel(CHANNEL_ID)
            if channel:
                # Check if it's the first morning alert of the day
                is_morning = (alert_time == "08:00" and day_type == 'weekday') or (alert_time == "10:00" and day_type == 'weekend')
                
                if is_morning and queued_morning_video is not None:
                    # Use the custom added video link, then erase it from memory
                    selected_video = queued_morning_video
                    queued_morning_video = None
                else:
                    # Pull from the default bank of URLs
                    selected_video = random.choice(TIKTOK_BANK)
                
                await channel.send(f"{alert_msg}\n{selected_video}")
                break

# Run web routing and discord gateway on concurrent threads
threading.Thread(target=run_web_server).start()
bot.run(TOKEN)


