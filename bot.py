import discord
from discord.ext import commands, tasks
import aiohttp
from aiohttp import web
import datetime
import os
import asyncio

# Configure Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Command prefix set to '?'
bot = commands.Bot(command_prefix='?', intents=intents)

# Globale Speicher-Variablen
executor_status_msg_id = None
roblox_version_msg_id = None
last_versions = {}  # Merkt sich den letzten Stand aller Plattformen (Windows, Mac, Android, iOS)


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
    print(f'Bot is online as {bot.user.name}!')
    if not auto_check_updates.is_running():
        auto_check_updates.start()


# -------------------------------------------------------------------
# FEATURE 1: Honeypot (#not-general) -> Auto-Ban
# -------------------------------------------------------------------
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if "not-general" in message.channel.name.lower():
        try:
            await message.delete()
            await message.guild.ban(
                message.author, 
                reason="Honeypot triggered in #not-general (Raid/Bot protection)", 
                delete_message_days=1
            )
            print(f"[HONEYPOT] {message.author} was automatically banned.")
        except discord.Forbidden:
            print(f"[ERROR] Missing permissions to ban {message.author}.")
        except Exception as e:
            print(f"[ERROR] {e}")
        return

    await bot.process_commands(message)


# -------------------------------------------------------------------
# FEATURE 2: Roblox Versions & Executors Tracker (Every 30 Mins)
# -------------------------------------------------------------------
@tasks.loop(minutes=30)
async def auto_check_updates():
    global executor_status_msg_id, roblox_version_msg_id, last_versions

    # 1. Roblox Versions Abrufen
    urls = {
        "Windows": "https://setup.rbxcdn.com/version",
        "Mac": "https://setup.rbxcdn.com/mac/version",
        "Android": "https://setup.rbxcdn.com/channel/common/deploy-android-app-version",
        "iOS": "https://setup.rbxcdn.com/channel/common/deploy-ios-app-version"
    }

    current_versions = {}
    async with aiohttp.ClientSession() as session:
        for platform, url in urls.items():
            try:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        current_versions[platform] = (await resp.text()).strip()
                    else:
                        current_versions[platform] = "Error fetching"
            except Exception:
                current_versions[platform] = "Error"

    # Prüfen auf Änderungen bei Roblox
    if current_versions != last_versions:
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
    async with aiohttp.ClientSession() as session:
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
                        for exec_name, info in list(data.items())[:10]:
                            status = info.get("status", "Unknown") if isinstance(info, dict) else str(info)
                            embed_exec.add_field(name=exec_name, value=f"Status: **{status}**", inline=True)
                    elif isinstance(data, list):
                        for item in data[:10]:
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
        except Exception as e:
            print(f"[ERROR] Executor fetch failed: {e}")


# -------------------------------------------------------------------
# MAIN RUNNER
# -------------------------------------------------------------------
async def main():
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        print("CRITICAL ERROR: 'DISCORD_TOKEN' environment variable is missing!")
        return

    # Start Dummy Webserver für Render
    await start_web_server()
    
    # Start Discord Bot
    async with bot:
        await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())
