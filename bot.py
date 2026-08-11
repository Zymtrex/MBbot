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
async def fetch_executor_status():
    async with aiohttp.ClientSession() as session:
        try:
            # Versuche, die Daten abzurufen
            async with session.get("https://weao.xyz/api/status/exploits", timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Wenn die API eine Liste direkt zurückgibt
                    return data
        except Exception as e:
            print(f"[ERROR] API failed: {e}")
    return None

# 4. COMMANDS
@bot.event
async def on_ready():
    print(f"Bot is ready: {bot.user}")

@bot.command(name="roblox")
async def roblox(ctx):
    async with aiohttp.ClientSession() as session:
        async with session.get("https://weao.xyz/api/versions/current") as resp:
            data = await resp.json()
            embed = discord.Embed(title="🎮 Roblox Current Versions", color=0x3498db)
            win = data.get("WindowsPlayer", {}).get("version") or "N/A"
            mac = data.get("MacPlayer", {}).get("version") or "N/A"
            embed.add_field(name="Windows", value=f"`{win}`", inline=True)
            embed.add_field(name="macOS", value=f"`{mac}`", inline=True)
            await ctx.send(embed=embed)

@bot.command(name="executors")
async def executors(ctx):
    data = await fetch_executor_status()
    if not data:
        await ctx.send("❌ Failed to reach API or invalid data.")
        return

    embed = discord.Embed(title="📡 Executor Status Overview", color=0x5865f2)
    # Begrenzung auf 25 Einträge, um den 400 Bad Request Fehler zu vermeiden
    items = list(data)[:25]
    
    for item in items:
        name = item.get("title") or "Unknown"
        updated = item.get("updated")
        status_str = "🟢 **UPDATED**" if updated else "🔴 **NOT UPDATED**"
        embed.add_field(name=f"**{name}**", value=status_str, inline=True)
        
    await ctx.send(embed=embed)

@bot.command(name="supdate")
async def supdate(ctx, *, update_text: str = None):
    try: await ctx.message.delete()
    except: pass
    if not update_text: return
    embed = discord.Embed(title="🔄 New Update", description=update_text, color=0x2ecc71)
    embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
    await ctx.send(embed=embed)

bot.run(os.environ.get("DISCORD_TOKEN"))
