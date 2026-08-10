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

# Store message ID for editing the exact same message every 30 minutes
status_message_id = None

# Dummy Webserver für Render Port-Binding
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
    # Start the 30-minute background loop
    if not auto_check_executors.is_running():
        auto_check_executors.start()


# -------------------------------------------------------------------
# FEATURE 1: Honeypot (#not-general) -> Auto-Ban
# -------------------------------------------------------------------
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Check if the message was sent in #not-general
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
            print(f"[ERROR] Missing permissions to ban {message.author}. Check bot role position.")
        except Exception as e:
            print(f"[ERROR] {e}")
        return

    await bot.process_commands(message)


# -------------------------------------------------------------------
# FEATURE 2: Auto-Update Executors every 30 Minutes
# -------------------------------------------------------------------
@tasks.loop(minutes=30)
async def auto_check_executors():
    global status_message_id

    await bot.wait_until_ready()

    target_channel = None
    for guild in bot.guilds:
        target_channel = discord.utils.get(guild.text_channels, name="📡executors") or \
                         discord.utils.get(guild.text_channels, name="executors")
        if target_channel:
            break

    if not target_channel:
        print("[EXECUTORS] Could not find channel '📡executors'.")
        return

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("https://weao.xyz/api/status/exploits") as response:
                if response.status == 200:
                    data = await response.json()

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

                        # Exact WEAO Status Key
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

                    if status_message_id:
                        try:
                            msg = await target_channel.fetch_message(status_message_id)
                            await msg.edit(embeds=embeds_list)
                            print("[EXECUTORS] Status message updated successfully.")
                            return
                        except discord.NotFound:
                            status_message_id = None

                    new_msg = await target_channel.send(embeds=embeds_list)
                    status_message_id = new_msg.id
                    print("[EXECUTORS] Posted new status message.")

                else:
                    print(f"[EXECUTORS] API returned status code {response.status}")
        except Exception as e:
            print(f"[EXECUTORS] Error fetching status: {e}")


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

    target_channel = discord.utils.get(
        ctx.guild.text_channels, 
        name="🔄updates"
    ) or discord.utils.get(
        ctx.guild.text_channels, 
        name="updates"
    ) or ctx.channel

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
    # Start dummy web server for Render
    await start_web_server()
    # Start bot
    await bot.start('MTUzNjE2NDA2NTIwMDgzNjYxOA.Gn_AvI.xUxrdgDOEmbWMJgJJ0LnGMygvmkrJzTthkR66U')

if __name__ == "__main__":
    asyncio.run(main())
