import os
import threading
import asyncio
from datetime import datetime
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
        .header {
            text-align: center;
            margin-bottom: 40px;
        }
        .header h1 {
            font-size: 2.5rem;
            color: #ffffff;
            margin-bottom: 10px;
        }
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: #202024;
            border: 1px solid #2e2e38;
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 0.9rem;
        }
        .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background-color: #f75a68;
            box-shadow: 0 0 10px #f75a68;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            max-width: 1100px;
            width: 100%;
        }
        .card {
            background-color: #18181b;
            border: 1px solid #27272a;
            border-radius: 12px;
            padding: 24px;
            transition: transform 0.2s, border-color 0.2s;
        }
        .card:hover {
            transform: translateY(-3px);
            border-color: #3f3f46;
        }
        .card-title {
            font-size: 1.2rem;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .card-desc {
            font-size: 0.95rem;
            color: #a1a1aa;
            line-height: 1.5;
            margin-bottom: 16px;
        }
        .channel-box {
            background: #09090b;
            border-left: 3px solid #5865f2;
            padding: 10px 14px;
            border-radius: 4px;
            font-size: 0.85rem;
            color: #d4d4d8;
        }
        .channel-name {
            background: #27272a;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: monospace;
            color: #38bdf8;
        }
    </style>
</head>
<body>

    <div class="header">
        <h1>MoneyBitch Bot Dashboard</h1>
        <div class="status-badge">
            <span class="status-dot"></span>
            <span style="color: #f75a68;">OFFLINE</span>
        </div>
    </div>

    <div class="grid">
        <!-- Roblox Tracker -->
        <div class="card">
            <div class="card-title">🎮 Roblox Version Tracker</div>
            <div class="card-desc">
                Checks current Roblox client versions across Windows, Mac, Android, and iOS every 30 minutes.
            </div>
            <div class="channel-box">
                Run <span class="channel-name">?roblox</span> in any channel to display and auto-update status there.
            </div>
        </div>

        <!-- Executor Status -->
        <div class="card">
            <div class="card-title">📡 Executor Status</div>
            <div class="card-desc">
                Provides a live status overview showing which executors are updated and ready to use.
            </div>
            <div class="channel-box">
                Run <span class="channel-name">?executors</span> in any channel to display and auto-update status there.
            </div>
        </div>

        <!-- Honeypot -->
        <div class="card">
            <div class="card-title">🛡️ Honeypot Raid Protection</div>
            <div class="card-desc">
                Protects your server against bot raids by setting up automated traps in dedicated protection channels.
            </div>
            <div class="channel-box">
                You must add a channel named exactly: <span class="channel-name">not-general</span>
            </div>
        </div>

        <!-- Permissions -->
        <div class="card">
            <div class="card-title">🔑 Roles & Command Permissions</div>
            <div class="card-desc">
                To execute commands (?ping, ?roblox, ?executors, ?supdate, ?clear), users must have Administrator permissions or one of the required roles.
            </div>
            <div class="channel-box">
                Required Roles: <span class="channel-name">owner</span> <span class="channel-name">moneybitch</span> <span class="channel-name">head staff</span> <span class="channel-name">mod</span>
            </div>
        </div>
    </div>

</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_flask, daemon=True).start()

# ---------------------------------------------------------
# 2. BOT CONFIGURATION
# ---------------------------------------------------------
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="?", intents=intents)

# Sets to store channel IDs where auto-updates should post every 30 mins
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
    url = "https://weao.xyz/api/versions/current"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            print(f"Error fetching Roblox versions: {e}")
    return None

async def fetch_executor_status():
    url = "https://weao.xyz/api/status/exploits"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            print(f"Error fetching Executor status: {e}")
    return None

def build_roblox_embed(data):
    embed = discord.Embed(
        title="🎮 Roblox Current Versions",
        color=discord.Color.from_rgb(52, 152, 219),
        timestamp=datetime.utcnow()
    )
    if not data:
        embed.description = "❌ Failed to retrieve Roblox versions."
        return embed

    # Mapping platform keys from API response
    platforms = {
        "WindowsPlayer": "💻 Windows",
        "MacPlayer": "🍎 macOS",
        "Android": "📱 Android",
        "iOS": "📱 iOS"
    }

    for key, name in platforms.items():
        ver_info = data.get(key, {})
        version = ver_info.get("version", "Unknown") if isinstance(ver_info, dict) else str(ver_info)
        embed.add_field(name=name, value=f"`{version}`", inline=True)

    embed.set_footer(text="Auto-updates every 30 min | Source: weao.xyz | MoneyBitch Bot v1.0.5")
    return embed

def build_executors_embed(data):
    embed = discord.Embed(
        title="📡 Executor Status Overview",
        color=discord.Color.from_rgb(88, 101, 242),
        timestamp=datetime.utcnow()
    )
    if not data:
        embed.description = "❌ Failed to retrieve executor status."
        return embed

    # Data is expected to be a list of executor objects
    for item in data:
        name = item.get("title", item.get("name", "Unknown"))
        version = item.get("version", "N/A")
        
        # Check boolean or string for updated status
        raw_updated = item.get("updated", False)
        is_updated = str(raw_updated).lower() in ["true", "1", "yes"]

        status_str = "🟢 **UPDATED**" if is_updated else "🔴 **NOT UPDATED**"

        embed.add_field(
            name=f"**{name}**",
            value=f"Status: {status_str}\nVersion: `{version}`",
            inline=True
        )

    embed.set_footer(text="Auto-updates every 30 min | Source: weao.xyz | MoneyBitch Bot v1.0.5")
    return embed

# ---------------------------------------------------------
# 4. BACKGROUND TASK (30 MIN AUTO-UPDATE)
# ---------------------------------------------------------
@tasks.loop(minutes=30)
async def auto_update_loop():
    await bot.wait_until_ready()
    
    # Update Roblox Channels
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

    # Update Executor Channels
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
        await ctx.send("❌ Please provide an update text! Example: `?supdate \"updated with noclip\"`", delete_after=5)
        return

    clean_text = update_text.strip('"\'')

    embed = discord.Embed(
        title="🔄 New Update",
        description=clean_text,
        color=discord.Color.from_rgb(46, 204, 113),
        timestamp=datetime.utcnow()
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
async def roblox_cmd(ctx):
    roblox_channels.add(ctx.channel.id)
    data = await fetch_roblox_versions()
    embed = build_roblox_embed(data)
    await ctx.send(embed=embed)

@bot.command(name="executors")
async def executors_cmd(ctx):
    executor_channels.add(ctx.channel.id)
    data = await fetch_executor_status()
    embed = build_executors_embed(data)
    await ctx.send(embed=embed)

# ---------------------------------------------------------
# 6. RUN BOT
# ---------------------------------------------------------
TOKEN = os.environ.get("DISCORD_TOKEN", "YOUR_BOT_TOKEN_HERE")
bot.run(TOKEN)
