import discord
from discord.ext import commands
import asyncio
import os

TOKEN = os.environ.get("TOKEN")

# churchmate
GUILD_ID_1 = 803650819462529095
VOICE_CHANNEL_ID_1 = 899659131068231731
# agent orange
GUILD_ID_2 = 1504814669938954260
VOICE_CHANNEL_ID_2 = 1504814670551318534

GUEST_ROLE_NAME = "Guest"
TIMEOUT_MINUTES = 20

SERVERS = {
    GUILD_ID_1: VOICE_CHANNEL_ID_1,
    GUILD_ID_2: VOICE_CHANNEL_ID_2,
}

pending_kicks = {}  # {member_id: asyncio.Task}

intents = discord.Intents.default()
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot is online as {bot.user}")

async def kick_if_no_voice(member, guild):
    await asyncio.sleep(TIMEOUT_MINUTES * 60)

    member = guild.get_member(member.id)
    if member is None:
        pending_kicks.pop(member.id, None)
        return

    # Fix 1: skip kick if guest role was manually removed
    role = discord.utils.get(guild.roles, name=GUEST_ROLE_NAME)
    if role and role not in member.roles:
        print(f"Skipping kick for {member.name} — Guest role already removed")
        pending_kicks.pop(member.id, None)
        return

    voice_channel_id = SERVERS[guild.id]
    if member.voice is None or member.voice.channel.id != voice_channel_id:
        try:
            await member.kick(reason=f"Did not join guest voice channel within {TIMEOUT_MINUTES} minutes")
            print(f"Kicked {member.name} from {guild.name} for not joining voice")
        except discord.Forbidden:
            print(f"Could not kick {member.name} - missing permissions")

    pending_kicks.pop(member.id, None)

@bot.event
async def on_member_join(member):
    guild = member.guild
    if guild.id not in SERVERS:
        return

    role = discord.utils.get(guild.roles, name=GUEST_ROLE_NAME)
    if role:
        for attempt in range(3):
            try:
                await member.add_roles(role)
                print(f"Assigned Guest role to {member.name} in {guild.name}")
                break
            except discord.HTTPException as e:
                if e.status == 429:
                    retry_after = getattr(e, "retry_after", 5)
                    print(f"Rate limited, retrying in {retry_after}s...")
                    await asyncio.sleep(retry_after)
                else:
                    print(f"Failed to assign role: {e}")
                    break

    # Fix 2: store task so it can be cancelled on role removal
    task = asyncio.create_task(kick_if_no_voice(member, guild))
    pending_kicks[member.id] = task

@bot.event
async def on_member_update(before, after):
    guild = after.guild
    if guild.id not in SERVERS:
        return

    # Fix 2: cancel pending kick if Guest role was manually removed
    role = discord.utils.get(guild.roles, name=GUEST_ROLE_NAME)
    if role and role in before.roles and role not in after.roles:
        task = pending_kicks.pop(after.id, None)
        if task:
            task.cancel()
            print(f"Cancelled pending kick for {after.name} — Guest role removed")

@bot.event
async def on_voice_state_update(member, before, after):
    guild = member.guild
    if guild.id not in SERVERS:
        return

    voice_channel_id = SERVERS[guild.id]
    if before.channel and before.channel.id == voice_channel_id:
        if after.channel is None or after.channel.id != voice_channel_id:
            role = discord.utils.get(guild.roles, name=GUEST_ROLE_NAME)
            if role and role in member.roles:
                try:
                    await member.kick(reason="Guest left the voice channel")
                    print(f"Kicked {member.name} from {guild.name} for leaving guest channel")
                    # Clean up any pending timer task too
                    task = pending_kicks.pop(member.id, None)
                    if task:
                        task.cancel()
                except discord.Forbidden:
                    print(f"Could not kick {member.name} - missing permissions")

bot.run(TOKEN)
