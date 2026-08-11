import os
import threading
from datetime import datetime
import aiohttp
import discord
from discord.ext import commands
from flask import Flask

# ---------------------------------------------------------
# 1. FLASK WEB SERVER (Verhindert Render Port/Timeout Crash)
# ---------------------------------------------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "MoneyBitch Bot status: ONLINE"

def run_flask():
    # Render weist automatisch einen PORT über die Umgebungsvariable zu
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# Startet den Webserver in einem separaten Thread
threading.Thread(target=run_flask, daemon=True).start()

# ---------------------------------------------------------
# 2. BOT CONFIGURATION
# ---------------------------------------------------------
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="?", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("MoneyBitch Bot is fully operational!")

# ---------------------------------------------------------
# 3. COMMANDS
# ---------------------------------------------------------

@bot.command(name="ping")
async def ping(ctx):
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! Latenz: `{latency}ms`")

@bot.command(name="supdate")
async def supdate(ctx, *, update_text: str = None):
    # Nachricht des Absenders löschen für ein sauberes Bild
    try:
        await ctx.message.delete()
    except Exception:
        pass

    if not update_text:
        await ctx.send("❌ Bitte gib eine Beschreibung an! Beispiel: `?supdate updated with noclip`", delete_after=5)
        return

    # Modernes, professionelles Embed
    embed = discord.Embed(
        title="🔄 New Update",
        description=f"```{update_text}```",
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

@bot.command(name="executors")
async def executors(ctx):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("https://whatexpsare.online/api/val", timeout=10) as response:
                if response.status != 200:
                    await ctx.send("⚠️ Fehler beim Abrufen der Executor-API.")
                    return
                data = await response.json()
        except Exception:
            await ctx.send("❌ Verbindung zur Executor-API fehlgeschlagen.")
            return

    embed = discord.Embed(
        title="📡 Executor Status Overview",
        color=discord.Color.from_rgb(88, 101, 242)
    )

    for item in data:
        name = item.get("title", item.get("name", "Unknown"))
        version = item.get("version", "N/A")
        
        # Robuster Check auf Boolean, String oder Integer Wert
        raw_updated = item.get("updated", False)
        is_updated = str(raw_updated).lower() in ["true", "1", "yes"]

        status_str = "🟢 **UPDATED**" if is_updated else "🔴 **NOT UPDATED**"

        embed.add_field(
            name=f"**{name}**",
            value=f"Status: {status_str}\nVersion: `{version}`",
            inline=True
        )

    embed.set_footer(text="Auto-updates every 30 min | Source: weao.xyz | MoneyBitch Bot v1.0.5")
    await ctx.send(embed=embed)

# ---------------------------------------------------------
# 4. BOT RUN
# ---------------------------------------------------------
TOKEN = os.environ.get("DISCORD_TOKEN", "DEIN_BOT_TOKEN_HIER")
bot.run(TOKEN)
