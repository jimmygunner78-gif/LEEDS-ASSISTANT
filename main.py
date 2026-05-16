import discord
from discord import app_commands
from discord.ext import tasks, commands
import datetime
import pytz
import random
from flask import Flask
import threading
import os

# --- WEB SERVER ENGINE ---
app = Flask('')
@app.route('/')
def home(): return "Leeds Assistant Bot is fully operational!"
def run_web_server(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

# --- BOT CONFIGURATION ---
TOKEN = os.environ.get('DISCORD_TOKEN')
ALERT_CHANNEL_ID = 1505124887189000214  
STRIKE_CHANNEL_ID = 1505179437585666169  
GUILD_ID = 1505104807382220870         
TIKTOK_BANK = ["https://tiktok.com", "https://tiktok.com"]
queued_morning_video = None
SCHEDULE = [('weekday', "08:00", "# @everyone ACTIVITY CHECK"), ('weekend', "10:00", "# @everyone ACTIVITY CHECK")] # Simplified for brevity

# --- ADVANCED FORCED SYNC ENGINE ---
class LeedsBotClient(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        guild_target = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild_target)
        await self.tree.sync(guild=guild_target)

bot = LeedsBotClient()

@bot.event
async def on_ready():
    if not scheduler_loop.is_running(): scheduler_loop.start()

# --- HELPER LOGIC ---
def is_authorized_staff(member: discord.Member) -> bool:
    return any(role.name.lower() in ["founder", "co-founder", "admin"] for role in member.roles)

def get_strike_message(member: discord.Member, number: int) -> str:
    return f"{member.mention} Strike {number}!"

# --- SLASH COMMANDS ---
@bot.tree.command(name="strike", description="Issue a strike")
@app_commands.describe(member="User", number="Level 1-5")
async def issue_strike(interaction: discord.Interaction, member: discord.Member, number: int):
    # IMMEDIATE RESPONSE TO AVOID TIMEOUT
    await interaction.response.send_message("🔄 Processing...", ephemeral=True)
    
    if not is_authorized_staff(interaction.user):
        return await interaction.edit_original_response(content="❌ Access Denied")

    strike_channel = bot.get_channel(STRIKE_CHANNEL_ID)
    msg = get_strike_message(member, number)

    # Perform action (simplified)
    await strike_channel.send(msg)
    await interaction.edit_original_response(content=f"✅ Strike {number} processed.")

@bot.tree.command(name="teststrike", description="Simulate a strike")
async def test_strike(interaction: discord.Interaction, member: discord.Member, number: int):
    await interaction.response.send_message("🔄 Testing...", ephemeral=True)
    strike_channel = bot.get_channel(STRIKE_CHANNEL_ID)
    await strike_channel.send(f"{get_strike_message(member, number)} (TEST)")
    await interaction.edit_original_response(content="👻 Test complete.")

# --- SCHEDULER & RUN ---
@tasks.loop(minutes=1)
async def scheduler_loop():
    # ... (existing scheduler logic)
    pass

threading.Thread(target=run_web_server).start()
bot.run(TOKEN)


