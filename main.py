import discord
from discord.ext import tasks, commands
import datetime
import pytz
import random
from flask import Flask
import threading

# --- WEB SERVER FOR RENDER/UPTIMEROBOT ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is online and running!"

def run_web_server():
    # Render automatically passes a PORT environment variable
    import os
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- CONFIGURATION ---
TOKEN = 'YOUR_BOT_TOKEN_HERE'  # Make sure your actual Discord token is here!
CHANNEL_ID = 123456789012345678  # Make sure your actual channel ID is here!

TIKTOK_BANK = [
    "https://tiktok.com",
    "https://tiktok.com"
]

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
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    if not scheduler_loop.is_running():
        scheduler_loop.start()

@tasks.loop(minutes=1)
async def scheduler_loop():
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
                random_video = random.choice(TIKTOK_BANK)
                await channel.send(f"{alert_msg}\n{random_video}")
                break

# Start the web server in a background thread before running the bot
threading.Thread(target=run_web_server).start()
bot.run(TOKEN)
