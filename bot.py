import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio
import os
from datetime import datetime
from aiohttp import web

# ==========================================
# BOT KONFIGURATION & VERSION
# ==========================================
BOT_VERSION = "1.0.5"
ALLOWED_ROLES = ["owner", "moneybitch", "head staff", "mod"]

EXECUTORS_API_URL = "https://weao.xyz/api/status/exploits"
ROBLOX_VERSION_API_URL = "https://weao.xyz/api/versions/current"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="?", intents=intents)


# ==========================================
# FAKE WEB SERVER FÜR RENDER (FREE TIER FIX)
# ==========================================
async def handle_ping(request):
    return web.Response(text="MoneyBitch Bot status: OK")

async def start_dummy_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    # Render weist den Port über die Umgebungsvariable PORT zu
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"[Render Fix] Dummy-Server erfolgreich gestartet auf Port {port}")


# ==========================================
# BERECHTIGUNGSPRÜFUNG
# ==========================================
def has_permission():
    async def predicate(ctx):
        if ctx.author.guild_permissions.administrator:
            return True
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
                    print(f"[API Error] {url} status {response.status}")
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
        win = data.get("Windows", data.get("win32", "N/A"))
        mac = data.get("Mac", data.get("macOS", "N/A"))
        android = data.get("Android", "N/A")
        ios = data.get("iOS", "N/A")

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
        return []

    embeds = []
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
        
        if count % 21 == 0:
            embeds.append(embed)
            embed = discord.Embed(color=discord.Color.purple())

    if len(embed.fields) > 0:
        embeds.append(embed)
        
    embeds[-1].set_footer(text=f"Auto-updates every 30 min | Source: weao.xyz | MoneyBitch Bot v{BOT_VERSION}")
    return embeds


# ==========================================
# EVENTS
# ==========================================
@bot.event
async def on_ready():
    print(f"==========================================")
    print(f"Bot eingeloggt als: {bot.user.name} (v{BOT_VERSION})")
    print(f"==========================================")
    
    # Fake Webserver starten für Render
    bot.loop.create_task(start_dummy_server())
    
    if not auto_update_status.is_running():
        auto_update_status.start()


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.channel.name == "not-general":
        try:
            await message.delete()
            await message.channel.send(
                f"🛡️ **Honeypot:** Keine Nachrichten in {message.channel.mention} erlaubt!",
                delete_after=8
            )
        except Exception as e:
            print(f"[Honeypot Error] {e}")
            
    await bot.process_commands(message)


# ==========================================
# COMMANDS
# ==========================================
@bot.command(name="ping")
@has_permission()
async def ping(ctx):
    await ctx.send(f"🏓 Pong! `{round(bot.latency * 1000)}ms`")


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
        await ctx.send("❌ **API currently unavailable.**")
        return

    embeds = create_executor_embeds(data)
    if not embeds:
        await ctx.send("❌ Keine Executor-Daten empfangen.")
        return

    for embed in embeds:
        await ctx.send(embed=embed)


@bot.command(name="supdate")
@has_permission()
async def supdate(ctx, *, text: str = None):
    await ctx.send("🔄 **Manuelles Update wird ausgeführt...**", delete_after=5)
    await run_auto_updates()


@bot.command(name="botinfo")
@has_permission()
async def botinfo(ctx):
    embed = discord.Embed(title="🤖 MoneyBitch Bot Info", color=discord.Color.green())
    embed.add_field(name="Bot Version", value=f"`v{BOT_VERSION}`", inline=True)
    embed.add_field(name="Erlaubte Rollen", value=", ".join([f"`{r}`" for r in ALLOWED_ROLES]), inline=False)
    await ctx.send(embed=embed)


@bot.command(name="clear")
@has_permission()
async def clear(ctx, amount: int = 5):
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🧹 `{amount}` Nachrichten gelöscht.", delete_after=4)


# ==========================================
# AUTOMATISCHE UPDATES
# ==========================================
async def run_auto_updates():
    for guild in bot.guilds:
        # 1. Roblox Channel
        roblox_channel = discord.utils.get(guild.text_channels, name="🔔roblox-version")
        if roblox_channel:
            data = await fetch_json(ROBLOX_VERSION_API_URL)
            if data:
                embed = create_roblox_embed(data)
                await roblox_channel.purge(limit=5)
                await roblox_channel.send(embed=embed)

        # 2. Executors Channel
        executors_channel = discord.utils.get(guild.text_channels, name="📡executors")
        if executors_channel:
            data = await fetch_json(EXECUTORS_API_URL)
            if data:
                embeds = create_executor_embeds(data)
                if embeds:
                    await executors_channel.purge(limit=5)
                    for embed in embeds:
                        await executors_channel.send(embed=embed)


@tasks.loop(minutes=30)
async def auto_update_status():
    await bot.wait_until_ready()
    await run_auto_updates()


# ==========================================
# BOT START
# ==========================================
TOKEN = os.getenv("DISCORD_TOKEN") or "DEIN_BOT_TOKEN_HIER"

if __name__ == "__main__":
    bot.run(TOKEN)
