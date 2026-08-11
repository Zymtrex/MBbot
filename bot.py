import os
import threading
import asyncio
from datetime import datetime, timezone
import aiohttp
import discord
from discord.ext import commands, tasks
from flask import Flask, render_template_string

# ---------------------------------------------------------
# 1. FLASK WEB SERVER & HTML DASHBOARD
# ---------------------------------------------------------
app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MoneyBitch Bot Dashboard</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #121214;
            color: #e1e1e6;
            display: flex;
            flex-direction: column;
            align-items: center;
            min-height: 100vh;
            padding: 40px 20px;
        }
        .header { text-align: center; margin-bottom: 40px; }
        .header h1 { font-size: 2.5rem; color: #ffffff; margin-bottom: 10px; }
        .status-badge {
            display: inline-flex; align-items: center; gap: 8px;
            background: #202024; border: 1px solid #2e2e38;
            padding: 8px 16px; border-radius: 20px; font-weight: 600; font-size: 0.9rem;
        }
        .status-dot {
            width: 10px; height: 10px; border-radius: 50%;
            background-color: #00e676; box-shadow: 0 0 10px #00e676;
        }
        .grid {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px; max-width: 1100px; width: 100%;
        }
        .card {
            background-color: #18181b; border: 1px solid #27272a;
            border-radius: 12px; padding: 24px;
        }
        .card-title { font-size: 1.2rem; font-weight: 700; color: #ffffff; margin-bottom: 12px; }
        .card-desc { font-size: 0.95rem; color: #a1a1aa; line-height: 1.5; margin-bottom: 16px; }
        .channel-box {
            background: #09090b; border-left: 3px solid #5865f2;
            padding: 10px 14px; border-radius: 4px; font-size: 0.85rem; color: #d4d4d8;
        }
        .channel-name { background: #27272a; padding: 2px 6px; border-radius: 4px; font-family: monospace; color: #38bdf8; }
    </style>
</head>
<body>
    <div class="header">
        <h1>MoneyBitch Bot Dashboard</h1>
        <div class="status-badge">
            <span class="status-dot"></span>
            <span style="color: #00e676;">ONLINE</span>
        </div>
    </div>
    <div class="grid">
        <div class="card">
            <div class="card-title">🎮 Roblox Version Tracker</div>
            <div class="card-desc">Checks current Roblox client versions every 30 minutes.</div>
            <div class="channel-box">Run <span class="channel-name">?roblox</span> in any channel.</div>
        </div>
        <div class="card">
            <div class="card-title">📡 Executor Status</div>
            <div class="card-desc">Provides live status overview showing updated executors.</div>
            <div class="channel-box">Run <span class="channel-name">?executors</span> in any channel.</div>
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_flask, daemon=True).start()

# ---------------------------------------------------------
# 2. BOT CONFIGURATION
# ---------------------------------------------------------
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="?", intents=intents)

roblox_channels = set()
executor_channels = set()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("MoneyBitch Bot is fully operational!")
    if not auto_update_loop.is_running():
        auto_update_loop.start()

# ---------------------------------------------------------
# 3. HELPER FUNCTIONS FOR APIs
# ---------------------------------------------------------
async def fetch_roblox_versions():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    async with aiohttp.ClientSession() as session:
        # Primär WEAO API
        try:
            async with session.get("https://weao.xyz/api/versions/current", headers=headers, timeout=5) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception:
            pass

        # Fallback WhatExpsAre API
        try:
            async with session.get("https://whatexpsare.online/api/versions", headers=headers, timeout=5) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            print(f"Error fetching Roblox versions: {e}")
            
    return None

async def fetch_executor_status():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("https://weao.xyz/api/status/exploits", headers=headers, timeout=5) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception:
            pass

        try:
            async with session.get("https://whatexpsare.online/api/status", headers=headers, timeout=5) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            print(f"Error fetching Executor status: {e}")

    return None

def build_roblox_embed(data):
    embed = discord.Embed(
        title="🎮 Roblox Current Versions",
        color=discord.Color.from_rgb(52, 152, 219),
        timestamp=datetime.now(timezone.utc)
    )
    if not data:
        embed.description = "❌ Failed to retrieve Roblox versions."
        return embed

    # WEAO Schlüssel sowie Fallback Key Mapping
    win = data.get("WindowsPlayer", {}).get("version") if isinstance(data.get("WindowsPlayer"), dict) else (data.get("WindowsPlayer") or data.get("Windows") or "Unknown")
    mac = data.get("MacPlayer", {}).get("version") if isinstance(data.get("MacPlayer"), dict) else (data.get("MacPlayer") or data.get("Mac") or "Unknown")
    android = data.get("Android", {}).get("version") if isinstance(data.get("Android"), dict) else (data.get("Android") or "Unknown")
    ios = data.get("iOS", {}).get("version") if isinstance(data.get("iOS"), dict) else (data.get("iOS") or "Unknown")

    embed.add_field(name="💻 Windows", value=f"`{win}`", inline=True)
    embed.add_field(name="🍎 macOS", value=f"`{mac}`", inline=True)
    embed.add_field(name="📱 Android", value=f"`{android}`", inline=True)
    embed.add_field(name="📱 iOS", value=f"`{ios}`", inline=True)

    embed.set_footer(text="Auto-updates every 30 min | Source: weao.xyz | MoneyBitch Bot v1.0.5")
    return embed

def build_executors_embed(data):
    embed = discord.Embed(
        title="📡 Executor Status Overview",
        color=discord.Color.from_rgb(88, 101, 242),
        timestamp=datetime.now(timezone.utc)
    )
    if not data:
        embed.description = "❌ Failed to retrieve executor status."
        return embed

    exec_list = data if isinstance(data, list) else list(data.values())

    # ALLE Executors anzeigen (ohne 15er Limit)
    for item in exec_list:
        name = item.get("title") or item.get("name") or "Unknown"
        version = item.get("version", "N/A")
        
        # Flexibler Check für alle möglichen Status-Keys der APIs
        is_updated = (
            item.get("isUpdated") is True or 
            item.get("updated") is True or 
            str(item.get("status")).lower() in ["working", "updated", "true", "1"] or
            str(item.get("updated")).lower() in ["true", "1"]
        )
        
        status_str = "🟢 **UPDATED**" if is_updated else "🔴 **NOT UPDATED**"

        embed.add_field(
            name=f"**{name}**",
            value=f"Status: {status_str}\nVersion: `{version}`",
            inline=True
        )

    embed.set_footer(text="Auto-updates every 30 min | Source: weao.xyz | MoneyBitch Bot v1.0.5")
    return embed

# ---------------------------------------------------------
# 4. BACKGROUND TASK
# ---------------------------------------------------------
@tasks.loop(minutes=30)
async def auto_update_loop():
    await bot.wait_until_ready()
    
    if roblox_channels:
        data = await fetch_roblox_versions()
        embed = build_roblox_embed(data)
        for channel_id in list(roblox_channels):
            channel = bot.get_channel(channel_id)
            if channel:
                try:
                    await channel.send(embed=embed)
                except Exception as e:
                    print(f"Failed to send Roblox update to channel {channel_id}: {e}")

    if executor_channels:
        data = await fetch_executor_status()
        embed = build_executors_embed(data)
        for channel_id in list(executor_channels):
            channel = bot.get_channel(channel_id)
            if channel:
                try:
                    await channel.send(embed=embed)
                except Exception as e:
                    print(f"Failed to send Executor update to channel {channel_id}: {e}")

# ---------------------------------------------------------
# 5. COMMANDS
# ---------------------------------------------------------
@bot.command(name="ping")
async def ping(ctx):
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! Latency: `{latency}ms`")

@bot.command(name="supdate")
async def supdate(ctx, *, update_text: str = None):
    try:
        await ctx.message.delete()
    except Exception:
        pass

    if not update_text:
        await ctx.send("❌ Please provide an update text!", delete_after=5)
        return

    clean_text = update_text.strip('"\'')

    embed = discord.Embed(
        title="🔄 New Update",
        description=clean_text,
        color=discord.Color.from_rgb(46, 204, 113),
        timestamp=datetime.now(timezone.utc)
    )

    embed.set_author(
        name=f"Published by {ctx.author.display_name}",
        icon_url=ctx.author.display_avatar.url
    )

    if bot.user.display_avatar:
        embed.set_thumbnail(url=bot.user.display_avatar.url)

    embed.set_footer(text="MoneyBitch System Announcement • Version v1.0.5")

    await ctx.send(embed=embed)

@bot.command(name="roblox")
async def roblox(ctx):
    roblox_channels.add(ctx.channel.id)
    data = await fetch_roblox_versions()
    embed = build_roblox_embed(data)
    await ctx.send(embed=embed)

@bot.command(name="executors", aliases=["executor"])
async def executors(ctx):
    executor_channels.add(ctx.channel.id)
    data = await fetch_executor_status()
    embed = build_executors_embed(data)
    await ctx.send(embed=embed)

# Honeypot Schutz
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.channel.name == "not-general":
        try:
            await message.author.ban(reason="Honeypot Trap triggered")
            await message.channel.send(f"🚨 User {message.author.mention} was banned for messaging in honeypot.")
        except Exception as e:
            print(f"Honeypot ban failed: {e}")
        return

    await bot.process_commands(message)

# ---------------------------------------------------------
# 6. RUN BOT
# ---------------------------------------------------------
TOKEN = os.environ.get("DISCORD_TOKEN", "YOUR_BOT_TOKEN_HERE")
bot.run(TOKEN)
