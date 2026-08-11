import discord
from discord.ext import commands, tasks
import aiohttp
from aiohttp import web
import datetime
import os
import asyncio

# -------------------------------------------------------------------
# CONFIGURATION / BERECHTIGUNGEN
# -------------------------------------------------------------------
# Trage hier die Namen oder IDs der Rollen ein, die die Befehle nutzen dürfen.
# Administratoren haben IMMER automatisch Zugriff!
# Beispiel: ALLOWED_ROLES = ["Admin", "Moderator", "VIP", 123456789012345678]
ALLOWED_ROLES = ["owner", "moneybitch", "head staff", "mod", ]

HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Configure Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='?', intents=intents)

# Globale Speicher-Variablen
executor_status_msg_id = None
roblox_version_msg_id = None
last_versions = {}


# -------------------------------------------------------------------
# PERMISSION CHECK FUNCTION
# -------------------------------------------------------------------
def is_allowed_user():
    async def predicate(ctx):
        # 1. Automatisch erlauben, wenn der User Administrator-Rechte hat
        if ctx.author.guild_permissions.administrator:
            return True
        
        # 2. Prüfen, ob der User eine der erlaubten Rollen besitzt
        if hasattr(ctx.author, "roles"):
            user_role_names = [role.name for role in ctx.author.roles]
            user_role_ids = [role.id for role in ctx.author.roles]
            
            for allowed in ALLOWED_ROLES:
                if allowed in user_role_names or allowed in user_role_ids:
                    return True
                    
        # Falls keine Bedingung zutrifft -> Fehler auslösen
        raise commands.MissingPermissions(["Administrator or Allowed Role"])
    return commands.check(predicate)


# -------------------------------------------------------------------
# DUMMY WEBSERVER FOR RENDER PORT BINDING
# -------------------------------------------------------------------
async def handle_ping(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"[WEB] Dummy server running on port {port}")


@bot.event
async def on_ready():
    print(f'✅ Bot logged in as: {bot.user.name} (ID: {bot.user.id})')
    print(f'🌐 Connected to {len(bot.guilds)} server(s).')
    if not auto_check_updates.is_running():
        auto_check_updates.start()


# -------------------------------------------------------------------
# ADVANCED LOGGING & ERROR HANDLER
# -------------------------------------------------------------------
@bot.event
async def on_command_completion(ctx):
    print(f"[COMMAND EXECUTED] User '{ctx.author}' (ID: {ctx.author.id}) used '{ctx.message.content}' in #{ctx.channel}")

@bot.event
async def on_command_error(ctx, error):
    print(f"[COMMAND FAILED] User '{ctx.author}' (ID: {ctx.author.id}) tried '{ctx.message.content}' in #{ctx.channel} -> Reason: {error}")

    # Wenn Rollen oder Admin-Rechte fehlen
    if isinstance(error, (commands.MissingPermissions, commands.CheckFailure)):
        try:
            await ctx.send(f"❌ You do not have permission or the required role to use this command, {ctx.author.mention}!")
        except discord.Forbidden:
            print(f"[PERM ERROR] Lacking permissions to send message in #{ctx.channel}")
    
    elif isinstance(error, commands.CommandNotFound):
        pass  # Unbekannte Befehle ignorieren

    else:
        try:
            await ctx.send(f"⚠️ An error occurred while executing this command: `{error}`")
        except discord.Forbidden:
            print(f"[PERM ERROR] Lacking permissions to send message in #{ctx.channel}")


# -------------------------------------------------------------------
# FEATURE 1: Honeypot (#not-general) & Message Event
# -------------------------------------------------------------------
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.content.startswith("?"):
        print(f"[COMMAND ATTEMPT] User '{message.author}' (ID: {message.author.id}) sent: '{message.content}' in #{message.channel}")

    # Honeypot Check
    if hasattr(message.channel, "name") and message.channel.name and "not-general" in message.channel.name.lower():
        try:
            await message.delete()
            await message.guild.ban(
                message.author, 
                reason="Honeypot triggered in #not-general (Raid/Bot protection)", 
                delete_message_days=1
            )
            print(f"[HONEYPOT] {message.author} was automatically banned.")
        except discord.Forbidden:
            print(f"[ERROR] Bot lacks permission to ban {message.author}.")
        except Exception as e:
            print(f"[ERROR] Honeypot error: {e}")
        return

    await bot.process_commands(message)


# -------------------------------------------------------------------
# FEATURE 2: Roblox Versions & Executors Tracker (Every 30 Mins)
# -------------------------------------------------------------------
@tasks.loop(minutes=30)
async def auto_check_updates():
    global executor_status_msg_id, roblox_version_msg_id, last_versions

    urls = {
        "Windows": "https://setup.rbxcdn.com/version",
        "Mac": "https://setup.rbxcdn.com/mac/version",
        "Android": "https://setup.rbxcdn.com/channel/common/deploy-android-app-version",
        "iOS": "https://setup.rbxcdn.com/channel/common/deploy-ios-app-version"
    }

    current_versions = {}
    timeout = aiohttp.ClientTimeout(total=10)

    # 1. Roblox Versions Abrufen
    async with aiohttp.ClientSession(headers=HTTP_HEADERS, timeout=timeout) as session:
        for platform, url in urls.items():
            try:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        current_versions[platform] = (await resp.text()).strip()
                    else:
                        current_versions[platform] = f"Error {resp.status}"
            except Exception as e:
                current_versions[platform] = f"Fetch Failed ({e})"

    if current_versions and current_versions != last_versions:
        last_versions = current_versions.copy()
        
        embed_roblox = discord.Embed(
            title="🎮 Roblox Version Update Status",
            description="Current deployment versions across platforms:",
            color=discord.Color.blue(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        for platform, ver in current_versions.items():
            embed_roblox.add_field(name=f"📱 {platform}", value=f"`{ver}`", inline=False)
        embed_roblox.set_footer(text="MoneyBitch Bot | Auto-Checked every 30m")

        for guild in bot.guilds:
            channel = discord.utils.get(guild.text_channels, name="🔔roblox-version")
            if channel:
                try:
                    await channel.send(embed=embed_roblox)
                except discord.Forbidden:
                    pass

    # 2. Executor Status Abrufen (whatexpsare.online)
    async with aiohttp.ClientSession(headers=HTTP_HEADERS, timeout=timeout) as session:
        try:
            async with session.get("https://whatexpsare.online/api/status") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    embed_exec = discord.Embed(
                        title="🛰️ Executor Status Tracker",
                        description="Live status overview from [whatexpsare.online](https://whatexpsare.online):",
                        color=discord.Color.green(),
                        timestamp=datetime.datetime.now(datetime.timezone.utc)
                    )
                    
                    if isinstance(data, dict):
                        for exec_name, info in list(data.items())[:12]:
                            status = info.get("status", "Unknown") if isinstance(info, dict) else str(info)
                            embed_exec.add_field(name=exec_name, value=f"Status: **{status}**", inline=True)
                    elif isinstance(data, list):
                        for item in data[:12]:
                            embed_exec.add_field(
                                name=item.get("name", "Unknown"), 
                                value=f"Status: **{item.get('status', 'Unknown')}**", 
                                inline=True
                            )

                    embed_exec.set_footer(text="MoneyBitch Bot | Sourced from whatexpsare.online")

                    for guild in bot.guilds:
                        channel = discord.utils.get(guild.text_channels, name="📡executors")
                        if channel:
                            try:
                                await channel.send(embed=embed_exec)
                            except discord.Forbidden:
                                pass
                else:
                    print(f"[ERROR] Executor API returned status code {resp.status}")
        except Exception as e:
            print(f"[ERROR] Executor fetch failed: {e}")


# -------------------------------------------------------------------
# FEATURE 3: RESTRICTED CHAT COMMANDS (Prefix: ?)
# -------------------------------------------------------------------
@bot.command(name="ping")
@is_allowed_user()
async def ping_command(ctx):
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! Latency: `{latency}ms`")


@bot.command(name="roblox")
@is_allowed_user()
async def roblox_command(ctx):
    urls = {
        "Windows": "https://setup.rbxcdn.com/version",
        "Mac": "https://setup.rbxcdn.com/mac/version",
        "Android": "https://setup.rbxcdn.com/channel/common/deploy-android-app-version",
        "iOS": "https://setup.rbxcdn.com/channel/common/deploy-ios-app-version"
    }
    current_versions = {}
    timeout = aiohttp.ClientTimeout(total=10)

    async with aiohttp.ClientSession(headers=HTTP_HEADERS, timeout=timeout) as session:
        for platform, url in urls.items():
            try:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        current_versions[platform] = (await resp.text()).strip()
                    else:
                        current_versions[platform] = f"Error {resp.status}"
            except Exception as e:
                current_versions[platform] = f"Fetch Failed ({e})"

    embed = discord.Embed(
        title="🎮 Roblox Version Status",
        color=discord.Color.blue(),
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    for platform, ver in current_versions.items():
        embed.add_field(name=f"📱 {platform}", value=f"`{ver}`", inline=False)
    embed.set_footer(text="MoneyBitch Bot")
    await ctx.send(embed=embed)


@bot.command(name="executors")
@is_allowed_user()
async def executors_command(ctx):
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(headers=HTTP_HEADERS, timeout=timeout) as session:
        try:
            async with session.get("https://whatexpsare.online/api/status") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    embed = discord.Embed(
                        title="🛰️ Executor Status Tracker",
                        description="Live status overview from [whatexpsare.online](https://whatexpsare.online):",
                        color=discord.Color.green(),
                        timestamp=datetime.datetime.now(datetime.timezone.utc)
                    )
                    if isinstance(data, dict):
                        for exec_name, info in list(data.items())[:12]:
                            status = info.get("status", "Unknown") if isinstance(info, dict) else str(info)
                            embed.add_field(name=exec_name, value=f"Status: **{status}**", inline=True)
                    elif isinstance(data, list):
                        for item in data[:12]:
                            embed.add_field(
                                name=item.get("name", "Unknown"), 
                                value=f"Status: **{item.get('status', 'Unknown')}**", 
                                inline=True
                            )
                    embed.set_footer(text="MoneyBitch Bot")
                    await ctx.send(embed=embed)
                else:
                    await ctx.send(f"❌ API currently unavailable (HTTP {resp.status}).")
        except Exception as e:
            await ctx.send(f"❌ Error fetching executor data: `{e}`")


@bot.command(name="botinfo")
@is_allowed_user()
async def botinfo_command(ctx):
    embed = discord.Embed(
        title="🤖 Bot Info",
        description="MoneyBitch Bot - Tracking & Moderation",
        color=discord.Color.purple()
    )
    embed.add_field(name="Prefix", value="`?`", inline=True)
    embed.add_field(name="Ping", value=f"`{round(bot.latency * 1000)}ms`", inline=True)
    embed.add_field(name="Commands", value="`?ping`, `?roblox`, `?executors`, `?botinfo`, `?clear`", inline=False)
    await ctx.send(embed=embed)


@bot.command(name="clear")
@is_allowed_user()
async def clear_command(ctx, amount: int = 5):
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🧹 Deleted {amount} messages.", delete_after=3)


# -------------------------------------------------------------------
# MAIN RUNNER
# -------------------------------------------------------------------
async def main():
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        print("CRITICAL ERROR: 'DISCORD_TOKEN' environment variable is missing!")
        return

    await start_web_server()
    
    async with bot:
        await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())
