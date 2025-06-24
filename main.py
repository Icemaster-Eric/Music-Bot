from typing import Literal
import os
import asyncio
import aiohttp
import discord
from discord.ext import commands
from discord import app_commands
import youtube_dl


intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
voice_client = None

playlists_path = "playlists"
playlists = [name for name in os.listdir(playlists_path) if os.path.isdir(os.path.join(playlists_path, name))]

ytdl_format_options = {
    "format": "bestaudio/best",
    "outtmpl": "playlists/%(title)s.%(ext)s",
    "restrictfilenames": True,
    "noplaylist": False,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "postprocessors": [{
        "key": "FFmpegExtractAudio",
        "preferredcodec": "mp3",
        "preferredquality": "192",
    }],
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

#print(ytdl.params.get("user_agent"))

#ytdl.download(["https://music.youtube.com/playlist?list=RDTMAK5uy_nuKPeaybq-IRcrMnaR-5TIfvKxB7fVJu0"])

#exit()


# commands (one playlist will always be on loop)
# /list (list playlists)
# /add-playlist (download playlist)
# /play (join vc and start playing)
# /stop (leave vc and stop playing)
# NOTE: Disconnect bot from vc if all members have left
# ⏮️⏭️🔁🔀🔉🔊


@bot.tree.command(name="list", description="List all available playlists")
async def list_playlists(interaction: discord.Interaction):
    embed = discord.Embed(title="Music Playlists", color=discord.Color.blurple())
    embed.set_footer(text="Use /play [name] to play any music playlist in a VC")

    for i, playlist in enumerate(playlists):
        embed.add_field(name=playlist, value="", inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="add-playlist", description="Download a YouTube music playlist")
async def add_playlist(interaction: discord.Interaction, link: str):
    await interaction.response.defer(ephemeral=True)

    print(ytdl.params.get("user_agent"))

    ytdl.download([link])

    await interaction.response.send_message("Successfully downloaded the playlist.", ephemeral=True)


@bot.tree.command(name="play", description="Play a music playlist in your VC")
async def music(interaction: discord.Interaction, playlist: str):
    # Ensure the command user is in a voice channel.
    if interaction.user.voice is None:
        await interaction.response.send_message("You must join a voice channel to play music.", ephemeral=True)
        return

    # Defer the response since processing might take a moment.
    await interaction.response.defer(ephemeral=True)

    try:
        loop = bot.loop
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(link, download=False))
    except Exception as e:
        await interaction.followup.send("Error extracting information from the link.")
        print(f"youtube_dl extraction error: {e}")
        return

    if data is None:
        await interaction.followup.send("Could not extract any information from the link.")
        return

    # If the data is a playlist, enqueue each track.
    if "entries" in data:
        entries = data["entries"]
        count = 0
        for entry in entries:
            if entry:
                await player.queue.put(entry)
                count += 1
        await interaction.followup.send(f"Added playlist with **{count}** tracks to the queue.")
    else:
        # Single track: enqueue it.
        await player.queue.put(data)
        title = data.get("title", "Unknown Title")
        await interaction.followup.send(f"Added **{title}** to the queue.")


"""
# /pause command: to pause current track
@bot.tree.command(name="pause", description="Pause the current track")
async def pause(interaction: discord.Interaction):
    # Ensure the command user is in a voice channel.
    if interaction.user.voice is None:
        await interaction.response.send_message("You must be in a voice channel to skip the current track.", ephemeral=True)
        return

    channel = interaction.user.voice.channel
    if channel in created_vcs:
        if interaction.user.id != created_vcs[channel]:
            await interaction.response.send_message("You must be the VC owner to skip the current track.", ephemeral=True)
            return

    if interaction.guild.id not in players:
        await interaction.response.send_message("Nothing is playing right now.", ephemeral=True)
        return

    player = players[interaction.guild.id]

    if player.voice_client.is_playing():
        if player.voice_client.is_paused():
            await interaction.response.send_message("The current track is already paused.", ephemeral=True)
        else:
            player.voice_client.pause()
            await interaction.response.send_message(f"{interaction.user.mention} has paused the current track.", silent=True)
    else:
        await interaction.response.send_message("No track is currently playing.", ephemeral=True)


# /pause command: to pause current track
@bot.tree.command(name="resume", description="Resume the current track")
async def pause(interaction: discord.Interaction):
    # Ensure the command user is in a voice channel.
    if interaction.user.voice is None:
        await interaction.response.send_message("You must be in a voice channel to skip the current track.", ephemeral=True)
        return

    channel = interaction.user.voice.channel
    if channel in created_vcs:
        if interaction.user.id != created_vcs[channel]:
            await interaction.response.send_message("You must be the VC owner to skip the current track.", ephemeral=True)
            return

    if interaction.guild.id not in players:
        await interaction.response.send_message("Nothing is playing right now.", ephemeral=True)
        return

    player = players[interaction.guild.id]

    if player.voice_client.is_playing():
        if player.voice_client.is_paused():
            player.voice_client.resume()
            await interaction.response.send_message(f"{interaction.user.mention} has resumed the current track.", silent=True)
        else:
            await interaction.response.send_message("The current track is already playing.", ephemeral=True)
    else:
        await interaction.response.send_message("No track is currently playing.", ephemeral=True)


# --- /skip command: to skip the current track ---
@bot.tree.command(name="skip", description="Skip the current track")
async def skip(interaction: discord.Interaction):
    # Ensure the command user is in a voice channel.
    if interaction.user.voice is None:
        await interaction.response.send_message("You must be in a voice channel to skip the current track.", ephemeral=True)
        return

    channel = interaction.user.voice.channel
    if channel in created_vcs:
        if interaction.user.id != created_vcs[channel]:
            await interaction.response.send_message("You must be the VC owner to skip the current track.", ephemeral=True)
            return

    if interaction.guild.id not in players:
        await interaction.response.send_message("Nothing is playing right now.", ephemeral=True)
        return
    player = players[interaction.guild.id]
    if player.voice_client.is_playing():
        player.voice_client.stop()
        await interaction.response.send_message(f"{interaction.user.mention} has skipped the current track.", silent=True)
    else:
        await interaction.response.send_message("No track is currently playing.", ephemeral=True)


@bot.event
async def on_reaction_add(reaction: discord.Reaction, user: discord.User):
    if user.bot:
        return
"""


@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")


bot.run(os.environ["DISCORD_BOT_TOKEN"])
