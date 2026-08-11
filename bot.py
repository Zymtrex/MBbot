import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio
import os
from datetime import datetime

# ==========================================
# BOT KONFIGURATION & VERSION
# ==========================================
BOT_VERSION = "1.0.5"
ALLOWED_ROLES = ["owner", "moneybitch", "head staff", "mod"]

# Aktuelle API Endpunkte
EXECUTORS_API_URL = "https://weao.xyz/api/status/exploits"
ROBLOX_VERSION_API_URL = "https://weao.xyz/api/versions/current"

# Intent-Einstellungen
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="?", intents=intents)


# ==========================================
# BERECHTIGUNGSPRÜFUNG (CHECK)
# ==========================================
def has_permission():
    async def predicate(ctx):
        # Administrator-Rechte haben immer Zugriff
        if ctx.author.guild_permissions.administrator:
            return True
        
        # Prüfung auf definierte Rollen (nicht case-sensitive)
        user_roles = [role.name.lower() for role in ctx.author.roles]
        if any(allowed_role.lower() in user_roles for allowed_role in ALLOWED_ROLES):
            return True
            
        await ctx.send("❌ **Keine Berechtigung:** Du benötigst eine der berechtigten Rollen oder Administrator-Rechte.")
        return False
    return commands.check(predicate)


# ==========================================
# API HILFSFUNKTIONEN
# ==========================================
async def fetch_json(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    print(f"[API Error] {url} returned status {response.status}")
                    return None
        except Exception as e:
            print(f"[API Fetch Exception] {e}")
            return None


def create_roblox_embed(data):
    embed = discord.Embed(
        title="🎮 Roblox Version Status",
        description="Current deployment versions across platforms:",
        color=discord.Color.blue()
    )
    
    if data:
        # Erwarte API Struktur oder Fallback
        win = data.get("Windows", data.get("win32", "N/A"))
        mac = data.get("Mac", data.get("macOS", "N/A"))
        android = data.get("Android", "Error 403")
        ios = data.get("iOS", "Error 403")

        embed.add_field(name="🟦 Windows", value=f"`{win}`", inline=False)
        embed.add_field(name="🟦 Mac", value=f"`{mac}`", inline=False)
        embed.add_field(name="🟦 Android", value=f"`{android}`", inline=False)
        embed.add_field(name="🟦 iOS", value=f"`{ios}`", inline=False)
    else:
        embed.add_field(name="Fehler", value="Konnte Versionsdaten nicht abrufen.", inline=False)

    embed.set_footer(text=f"MoneyBitch Bot v{BOT_VERSION} • {datetime.now().strftime('%H:%M')}")
    return embed


def create_executor_embeds(data):
    if not data:
        embed = discord.Embed(
            title="❌ Fehler",
            description="API currently unavailable.",
            color=discord.Color.red()
        )
        return [embed]

    embeds = []
    # Verarbeite Liste oder Dictionary von Exploits
    items = data if isinstance(data, list) else data.get("exploits", [])
    
    embed = discord.Embed(
        title="📡 Executor Status Overview",
        color=discord.Color.purple()
    )
    
    count = 0
    for item in items:
        name = item.get("title", item.get("name", "Unknown"))
        updated = item.get("updated", item.get("isUpdated", False))
        version = item.get("version", "N/A")
        
        status_str = "🟢 **UPDATED**" if updated else "🔴 **NOT UPDATED**"
        
        embed.add_field(
            name=f"**{name}**",
            value=f"Status: {status_str}\nVersion: `{version}`",
            inline=True
        )
        count += 1
        
        # Discord erlaubt maximal 25 Felder pro Embed
        if count % 21 == 0:
            embeds.append(embed)
            embed = discord.Embed(color=discord.Color.purple())

    if len(embed.fields) > 0:
        embeds.append(embed)
        
    embeds[-1].set_footer(text=f"Auto-updates every 30 min | Source: weao.xyz | MoneyBitch Bot v{BOT_VERSION}")
    return embeds


# ==========================================
# EVENTS & HONEYPOT
# ==========================================
@bot.event
async def on_ready():
    print(f"==========================================")
    print(f"Bot ist eingeloggt als: {bot.user.name}")
    print(f"Bot Version: {BOT_VERSION}")
    print(f"==========================================")
    
    # Starte automatische Hintergrund-Tasks
    if not auto_update_status.is_running():
        auto_update_status.start()


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Honeypot Raid Protection im Kanal 'not-general'
    if message.channel.name == "not-general":
        try:
            await message.delete()
            # Optional: Mitglied vorübergehend stummschalten (Timeout) oder verwarnen
            await message.channel.send(
                f"🛡️ **Honeypot ausgelöst:** Nachrichten in {message.channel.mention} sind nicht erlaubt! ({message.author.mention})",
                delete_after=10
            )
        except Exception as e:
            print(f"[Honeypot Error] {e}")
            
    await bot.process_commands(message)


# ==========================================
# BOT COMMANDS
# ==========================================
@bot.command(name="ping")
@has_permission()
async def ping(ctx):
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! Latenz: `{latency}ms`")


@bot.command(name="roblox")
@has_permission()
async def roblox(ctx):
    data = await fetch_json(ROBLOX_VERSION_API_URL)
    embed = create_roblox_embed(data)
    await ctx.send(embed=embed)


@bot.command(name="executors", aliases=["executor"])
@has_permission()
async def executors(ctx):
    data = await fetch_json(EXECUTORS_API_URL)
    if not data:
        await ctx.send("❌ **API currently unavailable (HTTP 404 / Connection Error).**")
        return

    embeds = create_executor_embeds(data)
    for embed in embeds:
        await ctx.send(embed=embed)


@bot.command(name="botinfo")
@has_permission()
async def botinfo(ctx):
    embed = discord.Embed(
        title="🤖 MoneyBitch Bot Status & Info",
        color=discord.Color.green()
    )
    embed.add_field(name="Bot Version", value=f"`v{BOT_VERSION}`", inline=True)
    embed.add_field(name="Prefix", value="`?`", inline=True)
    embed.add_field(name="Erlaubte Rollen", value=", ".join([f"`{r}`" for r in ALLOWED_ROLES]), inline=False)
    embed.set_footer(text="MoneyBitch Bot Protection & Utility")
    await ctx.send(embed=embed)


@bot.command(name="clear")
@has_permission()
async def clear(ctx, amount: int = 5):
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🧹 **{amount}** Nachrichten gelöscht.", delete_after=5)


# ==========================================
# AUTOMATISCHE 30-MINUTEN TASKS
# ==========================================
@tasks.loop(minutes=30)
async def auto_update_status():
    await bot.wait_until_ready()
    
    for guild in bot.guilds:
        # 1. Roblox Version Channel Update (🔔roblox-version)
        roblox_channel = discord.utils.get(guild.text_channels, name="🔔roblox-version")
        if roblox_channel:
            data = await fetch_json(ROBLOX_VERSION_API_URL)
            embed = create_roblox_embed(data)
            await roblox_channel.send(embed=embed)

        # 2. Executors Channel Update (📡executors)
        executors_channel = discord.utils.get(guild.text_channels, name="📡executors")
        if executors_channel:
            data = await fetch_json(EXECUTORS_API_URL)
            if data:
                embeds = create_executor_embeds(data)
                for embed in embeds:
                    await executors_channel.send(embed=embed)


# ==========================================
# BOT STARTEN
# ==========================================
TOKEN = os.getenv("DISCORD_TOKEN") or "DEIN_BOT_TOKEN_HIER"

if __name__ == "__main__":
    bot.run(TOKEN)
