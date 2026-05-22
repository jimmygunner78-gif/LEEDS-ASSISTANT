import discord
from discord.ext import tasks, commands
import datetime
import pytz
import random
from flask import Flask
import threading
import os

# --- ORIGINAL WEB SERVER FOR RENDER ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is online!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- BOT CONFIGURATION ---
TOKEN = os.environ.get('DISCORD_TOKEN')
CHANNEL_ID = 1505124887189000214  # Your text channel ID

# Your permanent database of TikTok links (Auto-boosted for mobile & PC)
TIKTOK_BANK = [
    "https://tikwm.com",
    "https://tikwm.com"
]

# --- ORIGINAL BOT SETUP ---
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    scheduler_loop.start()

# --- ORIGINAL TIMETABLE ENGINE ---
@tasks.loop(minutes=1)
async def scheduler_loop():
    await bot.wait_until_ready()
    
    tz = pytz.timezone('Europe/London')
    now = datetime.datetime.now(tz)
    
    current_time = now.strftime("%H:%M")
    day_of_week = now.weekday() # 0=Mon, 4=Fri, 5=Sat, 6=Sun
    day_type = 'weekend' if day_of_week >= 5 else 'weekday'
    
    # Defining the specific schedule exactly how you wanted it
    SCHEDULE = [
        # Weekdays (Monday to Friday)
        ('weekday', "08:00", "# @everyone ACTIVITY CHECK"),
        ('weekday', "16:00", "# @everyone REMINDER"),
        ('weekday', "18:00", "# @everyone REMINDER"),
        ('weekday', "20:00", "# @everyone REMINDER"),
        ('weekday', "22:00", "# @everyone FINAL REMINDER"),
        
        # Weekends (Saturday and Sunday)
        ('weekend', "10:00", "# @everyone ACTIVITY CHECK"),
        ('weekend', "12:00", "# @everyone REMINDER"),
        ('weekend', "13:00", "# @everyone REMINDER"),
        ('weekend', "15:00", "# @everyone REMINDER"),
        ('weekend', "17:00", "# @everyone REMINDER"),
        ('weekend', "20:00", "# @everyone REMINDER"),
        ('weekend', "22:00", "# @everyone FINAL REMINDER")
    ]
    
    for alert_type, alert_time, alert_msg in SCHEDULE:
        if alert_type == day_type and alert_time == current_time:
            channel = bot.get_channel(CHANNEL_ID)
            if channel:
                random_video = random.choice(TIKTOK_BANK)
                full_message = f"{alert_msg}\n{random_video}"
                await channel.send(full_message)
                break

# Start the web port thread for Render
threading.Thread(target=run_web_server, daemon=True).start()

# Launch the bot with your working environment token
bot.run(TOKEN)


