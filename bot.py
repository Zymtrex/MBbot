import os
import threading
import datetime
import aiohttp
import discord
from discord.ext import commands, tasks
from flask import Flask

# 1. FLASK WEB SERVER (Render keep-alive)
app = Flask(__name__)
@app.route('/')
def home(): 
    return "Bot is online"

threading.Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000))), daemon=True).start()

# 2. BOT SETUP
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="?", intents=intents)

status_message_id = None

# 3. API FUNCTIONS
async def fetch_roblox_versions():
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("https://weao.xyz/api/versions/current", timeout=10) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            print(f"[API ERROR] Roblox versions: {e}")
    return None

async def fetch_executor_status():
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("https://weao.xyz/api/status/exploits", timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if isinstance(data, dict):
                        return data.get("exploits") or list(data.values())
                    elif isinstance(data, list):
                        return data
        except Exception as e:
            print(f"[API ERROR] Executor status: {e}")
    return []

# 4. EVENTS & HONEYPOT
@bot.event
async def on_ready():
    print(f"Bot is ready: {bot.user}")
    if not auto_check_executors.is_running():
        auto_check_executors.start()

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Honeypot Schutz (#not-general) -> Auto-Ban
    if message.channel and "not-general" in message.channel.name.lower():
        try:
            await message.delete()
            await message.guild.ban(
                message.author, 
                reason="Honeypot triggered in #not-general (Raid/Bot protection)", 
                delete_message_days=7
            )
            print(f"[HONEYPOT] {message.author} was automatically banned.")
            return
        except discord.Forbidden:
            print(f"[ERROR] Missing permissions to ban {message.author}.")
        except Exception as e:
            print(f"[ERROR] Honeypot failure: {e}")

    await bot.process_commands(message)

# 5. BACKGROUND LOOP (30 Min Executor Update)
@tasks.loop(minutes=30)
async def auto_check_executors():
    global status_message_id
    await bot.wait_until_ready()

    target_channel = None
    for guild in bot.guilds:
        target_channel = (
            discord.utils.get(guild.text_channels, name="📡executors") or 
            discord.utils.get(guild.text_channels, name="executors")
        )
        if target_channel:
            break

    if not target_channel:
        return

    items = await fetch_executor_status()
    if not items:
        return

    embed = discord.Embed(
        title="📡 Executor Status Overview", 
        color=0x5865f2,
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )

    for item in items[:25]:
        if not isinstance(item, dict):
            continue
            
        name = item.get("title") or item.get("name") or item.get("displayName") or "Unknown"
        version = item.get("version", "N/A")
        
        updated_val = item.get("updateStatus")
        if updated_val is None:
            updated_val = item.get("isUpdated")
        if updated_val is None:
            updated_val = item.get("updated")

        is_updated = (
            updated_val is True or 
            updated_val == 1 or 
            str(updated_val).lower() in ["true", "1", "working", "up to date", "updated"]
        )
        
        status_str = "🟢 **UPDATED**" if is_updated else "🔴 **NOT UPDATED**"
        embed.add_field(name=name, value=f"Status: {status_str}\nVersion: `{version}`", inline=True)
        
    embed.set_footer(text="Auto-updates every 30 min | Source: weao.xyz | MoneyBitch Bot v1.0.5")

    if status_message_id:
        try:
            msg = await target_channel.fetch_message(status_message_id)
            await msg.edit(embed=embed)
            return
        except discord.NotFound:
            status_message_id = None

    new_msg = await target_channel.send(embed=embed)
    status_message_id = new_msg.id

# 6. COMMANDS
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
    items = await fetch_executor_status()
    embed = discord.Embed(title="📡 Executor Status Overview", color=0x5865f2)
    
    if not items:
        embed.description = "❌ No data received from WEAO API."
        await ctx.send(embed=embed)
        return

    for item in items[:25]:
        if not isinstance(item, dict):
            continue
            
        name = item.get("title") or item.get("name") or item.get("displayName") or "Unknown"
        version = item.get("version", "N/A")
        
        updated_val = item.get("updateStatus")
        if updated_val is None:
            updated_val = item.get("isUpdated")
        if updated_val is None:
            updated_val = item.get("updated")

        is_updated = (
            updated_val is True or 
            updated_val == 1 or 
            str(updated_val).lower() in ["true", "1", "working", "up to date", "updated"]
        )
        
        status_str = "🟢 **UPDATED**" if is_updated else "🔴 **NOT UPDATED**"
        embed.add_field(name=name, value=f"Status: {status_str}\nVersion: `{version}`", inline=True)
        
    embed.set_footer(text="Auto-updates every 30 min | Source: weao.xyz | MoneyBitch Bot v1.0.5")
    await ctx.send(embed=embed)

@bot.command(name="supdate")
@commands.has_permissions(administrator=True)
async def supdate(ctx, *, update_text: str = None):
    try: 
        await ctx.message.delete()
    except: 
        pass
    if not update_text: 
        return

    target_channel = (
        discord.utils.get(ctx.guild.text_channels, name="🔄updates") or 
        discord.utils.get(ctx.guild.text_channels, name="updates") or 
        ctx.channel
    )

    embed = discord.Embed(
        title="🔄 New Update", 
        description=update_text, 
        color=0x2ecc71,
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    if ctx.guild.icon:
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url)
    else:
        embed.set_author(name=ctx.guild.name)

    embed.set_footer(text=f"Published by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
    await target_channel.send(embed=embed)

bot.run(os.environ.get("DISCORD_TOKEN"))
