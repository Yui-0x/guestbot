import discord
from discord.ext import commands
import asyncio

import os
TOKEN = os.environ.get("MTUxNDUwNDAwODIzNTIyNTE4OA.GankWM.Tp_xI3tDpwsu2scCJuvMQCh0RwlrHjGt9RjvSI")
GUILD_ID = 803650819462529095          # Your server ID
VOICE_CHANNEL_ID = 899659131068231731  # Your guest voice channel ID
GUEST_ROLE_NAME = "Guest"     # Role name to assign guests
TIMEOUT_MINUTES = 20           # Kick if they don't join voice within this time

intents = discord.Intents.default()
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot is online as {bot.user}")

@bot.event
async def on_member_join(member):
    guild = bot.get_guild(GUILD_ID)
    if guild is None:
        return

    # Assign guest role
    role = discord.utils.get(guild.roles, name=GUEST_ROLE_NAME)
    if role:
        await member.add_roles(role)
        print(f"Assigned Guest role to {member.name}")

    # Start timeout — kick if they don't join voice in time
    await asyncio.sleep(TIMEOUT_MINUTES * 60)

    # Check if they're still in server and still not in voice
    member = guild.get_member(member.id)
    if member is None:
        return  # Already left

    if member.voice is None or member.voice.channel.id != VOICE_CHANNEL_ID:
        try:
            await member.kick(reason=f"Did not join guest voice channel within {TIMEOUT_MINUTES} minutes")
            print(f"Kicked {member.name} for not joining voice in time")
        except discord.Forbidden:
            print(f"Could not kick {member.name} - missing permissions")

@bot.event
async def on_voice_state_update(member, before, after):
    guild = bot.get_guild(GUILD_ID)
    if guild is None:
        return

    # Check if they left the guest voice channel
    if before.channel and before.channel.id == VOICE_CHANNEL_ID:
        if after.channel is None or after.channel.id != VOICE_CHANNEL_ID:
            role = discord.utils.get(guild.roles, name=GUEST_ROLE_NAME)
            if role and role in member.roles:
                try:
                    await member.kick(reason="Guest left the voice channel")
                    print(f"Kicked {member.name} for leaving guest channel")
                except discord.Forbidden:
                    print(f"Could not kick {member.name} - missing permissions")

bot.run(TOKEN)
