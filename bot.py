import os
import threading
import asyncio
from datetime import datetime, timezone
import aiohttp
import discord
from discord.ext import commands
from flask import Flask, render_template_string

# 1. FLASK WEB SERVER
app = Flask(__name__)
@app.route('/')
def home(): return "Bot is online"
threading.Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000))), daemon=True).start()

# 2. BOT SETUP
intents = discord.Intents.all() 
bot = commands.Bot(command_prefix="?", intents=intents)

# 3. LOGIC
async def fetch_executor_status():
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("https://weao.xyz/api/status/exploits", timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("exploits") or data.get("data") or data
        except: return None

# 4. COMMANDS
@bot.command(name="executors")
async def executors(ctx):
    data = await fetch_executor_status()
    if not data:
        await ctx.send("❌ Keine Daten verfügbar.")
        return

    items = list(data.values() if isinstance(data, dict) else (data if isinstance(data, list) else []))
    
    # FIX: Begrenzung auf 25, um den Discord Fehler zu verhindern
    items_to_show = items[:25]
    
    embed = discord.Embed(title="📡 Executor Status", color=0x5865f2)
    for item in items_to_show:
        if isinstance(item, dict):
            name = item.get("title") or item.get("name") or "Unknown"
            updated = item.get("isUpdated") or item.get("updated") or False
            status = "🟢 UPDATED" if updated else "🔴 NOT UPDATED"
            embed.add_field(name=name, value=status, inline=True)
            
    await ctx.send(embed=embed)

@bot.event
async def on_ready():
    print(f"Bot ist bereit: {bot.user}")

bot.run(os.environ.get("DISCORD_TOKEN"))
