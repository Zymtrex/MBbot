import os
import threading
import aiohttp
import discord
from discord.ext import commands
from flask import Flask

# 1. FLASK WEB SERVER
app = Flask(__name__)
@app.route('/')
def home(): return "Bot is online"
threading.Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000))), daemon=True).start()

# 2. BOT SETUP
intents = discord.Intents.all() 
bot = commands.Bot(command_prefix="?", intents=intents)

# 3. API FUNCTIONS
async def fetch_roblox_versions():
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("https://weao.xyz/api/versions/current", timeout=10) as resp:
                if resp.status == 200:
                    return await resp.json()
        except: pass
    return None

async def fetch_executor_status():
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("https://weao.xyz/api/status/exploits", timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if isinstance(data, dict):
                        return data.get("exploits") or data.get("data") or data
                    return data
        except: pass
    return None

# 4. COMMANDS
@bot.event
async def on_ready():
    print(f"Bot is ready: {bot.user}")

@bot.command(name="roblox")
async def roblox(ctx):
    data = await fetch_roblox_versions()
    embed = discord.Embed(title="🎮 Roblox Current Versions", color=0x3498db)
    if not data:
        embed.description = "❌ Failed to fetch versions."
    else:
        win = data.get("WindowsPlayer", {}).get("version") or data.get("Windows") or "Unknown"
        mac = data.get("MacPlayer", {}).get("version") or data.get("Mac") or "Unknown"
        android = data.get("AndroidPlayer", {}).get("version") or data.get("Android") or "2.733.988"
        ios = data.get("iOSPlayer", {}).get("version") or data.get("iOS") or "2.733.988"
        
        embed.add_field(name="💻 Windows", value=f"`{win}`", inline=True)
        embed.add_field(name="🍎 macOS", value=f"`{mac}`", inline=True)
        embed.add_field(name="📱 Android", value=f"`{android}`", inline=True)
        embed.add_field(name="📱 iOS", value=f"`{ios}`", inline=True)
        
    embed.set_footer(text="Auto-updates every 30 min | Source: weao.xyz | MoneyBitch Bot v1.0.5")
    await ctx.send(embed=embed)

@bot.command(name="executors", aliases=["executor"])
async def executors(ctx):
    data = await fetch_executor_status()
    embed = discord.Embed(title="📡 Executor Status Overview", color=0x5865f2)
    
    if not data:
        embed.description = "❌ No data received from WEAO API."
        await ctx.send(embed=embed)
        return

    items = list(data.values() if isinstance(data, dict) else (data if isinstance(data, list) else []))
    items_list = items[:25] # Discord 25-field limit fix
    
    for item in items_list:
        if not isinstance(item, dict):
            continue
        name = item.get("title") or item.get("name") or "Unknown"
        version = item.get("version", "N/A")
        
        # Verbesserte Logik zur Erkennung, ob updated/working
        is_updated = (
            item.get("isUpdated") is True or 
            item.get("updated") is True or 
            str(item.get("status")).lower() in ["working", "updated", "true", "1"] or
            str(item.get("updated")).lower() in ["true", "1"]
        )
        
        status_str = "🟢 **UPDATED**" if is_updated else "🔴 **NOT UPDATED**"
        embed.add_field(name=name, value=f"Status: {status_str}\nVersion: `{version}`", inline=True)
        
    embed.set_footer(text="Auto-updates every 30 min | Source: weao.xyz | MoneyBitch Bot v1.0.5")
    await ctx.send(embed=embed)

@bot.command(name="supdate")
async def supdate(ctx, *, update_text: str = None):
    try: await ctx.message.delete()
    except: pass
    if not update_text: return
    embed = discord.Embed(title="🔄 New Update", description=update_text, color=0x2ecc71)
    embed.set_author(name=f"{ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
    embed.set_footer(text="MoneyBitch Bot v1.0.5")
    await ctx.send(embed=embed)

bot.run(os.environ.get("DISCORD_TOKEN"))
