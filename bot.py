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

    await bot.wait_until_ready()

    async with aiohttp.ClientSession() as session:
        # --- PART A: ROBLOX VERSIONS CHECK ALL PLATFORMS ---
        try:
            async with session.get("https://weao.xyz/api/versions/current") as resp:
                if resp.status == 200:
                    vdata = await resp.json()

                    platforms = ["Windows", "Mac", "Android", "iOS"]
                    current_state = {}
                    updates_detected = []

                    for plat in platforms:
                        ver = vdata.get(plat, "N/A")
                        date_str = vdata.get(f"{plat}Date", "N/A")
                        current_state[plat] = ver

                        # Überprüfen, ob sich eine Version geändert hat
                        if plat in last_versions and last_versions[plat] != ver:
                            updates_detected.append((plat, last_versions[plat], ver))

                    # Speicher aktualisieren
                    first_run = len(last_versions) == 0
                    last_versions = current_state

                    # Kanal suchen
                    version_channel = None
                    for guild in bot.guilds:
                        version_channel = discord.utils.get(guild.text_channels, name="roblox-version") or \
                                          discord.utils.get(guild.text_channels, name="🔔roblox-version")
                        if version_channel:
                            break

                    if version_channel:
                        # 1. Haupt-Embed mit Übersicht aller Plattformen erstellen
                        overview_embed = discord.Embed(
                            title="🎮 Current Roblox Versions",
                            url="https://weao.xyz",
                            color=discord.Color.blue(),
                            timestamp=datetime.datetime.now(datetime.timezone.utc)
                        )

                        for plat in platforms:
                            ver = vdata.get(plat, "N/A")
                            dt = vdata.get(f"{plat}Date", "N/A")
                            overview_embed.add_field(
                                name=f"📱 {plat}" if plat in ["Android", "iOS"] else f"💻 {plat}",
                                value=f"Version: `{ver}`\nUpdated: `{dt}`",
                                inline=False
                            )

                        overview_embed.set_footer(text="Auto-updates every 30 min | Source: weao.xyz")

                        # Dashboard-Botschaft senden oder editieren
                        if roblox_version_msg_id:
                            try:
                                msg = await version_channel.fetch_message(roblox_version_msg_id)
                                await msg.edit(embed=overview_embed)
                                print("[ROBLOX] Updated main version dashboard embed.")
                            except discord.NotFound:
                                roblox_version_msg_id = None

                        if not roblox_version_msg_id:
                            new_msg = await version_channel.send(embed=overview_embed)
                            roblox_version_msg_id = new_msg.id
                            print("[ROBLOX] Posted initial main version dashboard embed.")

                        # 2. Falls es ein Update gab (und es nicht der allererste Start ist) -> Ping / Alert senden
                        if updates_detected and not first_run:
                            for plat, old_v, new_v in updates_detected:
                                alert_embed = discord.Embed(
                                    title=f"🚨 Roblox Update Detected for {plat}!",
                                    color=discord.Color.gold(),
                                    timestamp=datetime.datetime.now(datetime.timezone.utc)
                                )
                                alert_embed.add_field(name="Platform", value=plat, inline=True)
                                alert_embed.add_field(name="Old Version", value=f"`{old_v}`", inline=True)
                                alert_embed.add_field(name="New Version", value=f"`{new_v}`", inline=True)
                                alert_embed.set_footer(text="Auto-detected | WEAO API")
                                
                                await version_channel.send(embed=alert_embed)
                                print(f"[ROBLOX] Alert posted for {plat} update.")

        except Exception as e:
            print(f"[ERROR] Roblox Version Check: {e}")

        # --- PART B: EXECUTORS STATUS OVERVIEW ---
        try:
            async with session.get("https://weao.xyz/api/status/exploits") as resp:
                if resp.status == 200:
                    data = await resp.json()

                    exec_channel = None
                    for guild in bot.guilds:
                        exec_channel = discord.utils.get(guild.text_channels, name="executors") or \
                                       discord.utils.get(guild.text_channels, name="📡executors")
                        if exec_channel:
                            break

                    if exec_channel:
                        embeds_list = []
                        current_embed = discord.Embed(
                            title="🛰️ Executor Status Overview",
                            url="https://weao.xyz",
                            color=discord.Color.purple(),
                            timestamp=datetime.datetime.now(datetime.timezone.utc)
                        )

                        field_count = 0
                        for item in data:
                            if field_count >= 25:
                                embeds_list.append(current_embed)
                                current_embed = discord.Embed(
                                    color=discord.Color.purple(),
                                    timestamp=datetime.datetime.now(datetime.timezone.utc)
                                )
                                field_count = 0

                            name = item.get("title") or item.get("name", "Unknown")
                            version = item.get("version", "N/A")
                            updated = bool(item.get("updateStatus", False))

                            status_str = "🟢 **UPDATED**" if updated else "🔴 **NOT UPDATED**"
                            current_embed.add_field(
                                name=name,
                                value=f"Status: {status_str}\nVersion: `{version}`",
                                inline=True
                            )
                            field_count += 1

                        current_embed.set_footer(text="Auto-updates every 30 min | Source: weao.xyz")
                        embeds_list.append(current_embed)

                        if executor_status_msg_id:
                            try:
                                msg = await exec_channel.fetch_message(executor_status_msg_id)
                                await msg.edit(embeds=embeds_list)
                                print("[EXECUTORS] Status message updated.")
                            except discord.NotFound:
                                executor_status_msg_id = None

                        if not executor_status_msg_id:
                            new_msg = await exec_channel.send(embeds=embeds_list)
                            executor_status_msg_id = new_msg.id
                            print("[EXECUTORS] Posted new status message.")
        except Exception as e:
            print(f"[ERROR] Executors Check: {e}")


# -------------------------------------------------------------------
# FEATURE 3: Post Updates (?supdate <text>) (ADMIN ONLY)
# -------------------------------------------------------------------
@bot.command(name="supdate")
@commands.has_permissions(administrator=True)
async def send_update(ctx, *, update_text: str):
    try:
        await ctx.message.delete()
    except discord.Forbidden:
        pass

    target_channel = discord.utils.get(ctx.guild.text_channels, name="updates") or \
                     discord.utils.get(ctx.guild.text_channels, name="🔄updates") or ctx.channel

    embed = discord.Embed(
        title="🔄 New Update",
        description=update_text,
        color=discord.Color.green(),
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    if ctx.guild.icon:
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url)
    else:
        embed.set_author(name=ctx.guild.name)

    embed.set_footer(text=f"Published by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)

    await target_channel.send(embed=embed)


async def main():
    await start_web_server()
    # TRAGE HIER DEINEN BOT TOKEN EIN:
    await bot.start('MTUzNjE2NDA2NTIwMDgzNjYxOA.Gn_AvI.xUxrdgDOEmbWMJgJJ0LnGMygvmkrJzTthkR66U')

if __name__ == "__main__":
    asyncio.run(main())
