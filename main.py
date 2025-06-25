from typing import Literal
import os
import asyncio
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
playlist = asyncio.Queue()

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
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "postprocessors": [{
        "key": "FFmpegExtractAudio",
        "preferredcodec": "mp3",
        "preferredquality": "192",
    }],
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


# commands (one playlist will always be on loop)
# /list (list playlists)
# /add-playlist (download playlist)
# /play (join vc and start playing)
# /stop (leave vc and stop playing)
# NOTE: Disconnect bot from vc if all members have left
# ⏯️⏮️⏭️🔁🔀🔉🔊


async def play_next():
    if playlist.empty() or voice_client is None:
        return

    song_path = await playlist.get()
    source = discord.FFmpegPCMAudio(song_path)
    voice_client.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(), bot.loop))


@bot.tree.command(name="list", description="List all available playlists")
async def list_playlists(interaction: discord.Interaction):
    embed = discord.Embed(title="Music Playlists", color=discord.Color.blurple())
    embed.set_footer(text="Use /play [name] to play any music playlist in a VC")

    for i, playlist in enumerate(playlists):
        embed.add_field(name=playlist, value="", inline=True)

    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="add-playlist", description="Download a YouTube music playlist")
async def add_playlist(interaction: discord.Interaction, link: str):
    await interaction.response.send_message("This feature is currently disabled.", ephemeral=True)
    return

    await interaction.response.defer(ephemeral=True)

    print(ytdl.params.get("user_agent"))

    ytdl.download([link])

    await interaction.response.send_message("Successfully downloaded the playlist.", ephemeral=True)


@bot.tree.command(name="play", description="Play a music playlist in your VC")
async def play(interaction: discord.Interaction, playlist_name: str):
    global voice_client
    # Ensure the command user is in a voice channel.
    if interaction.user.voice is None: # type: ignore
        await interaction.response.send_message("You must join a voice channel to play music.", ephemeral=True)
        return

    if voice_client is not None:
        await interaction.response.send_message("Already playing music in a voice channel.", ephemeral=True)
        return

    # Defer the response since processing might take a moment.
    await interaction.response.defer(ephemeral=True)

    for mp3_file in os.listdir(f"playlists/{playlist_name}"):
        if mp3_file.endswith(".mp3"):
            await playlist.put(f"playlists/{playlist_name}/{mp3_file}")

    voice_client = await interaction.user.voice.channel.connect() # type: ignore

    await voice_client.channel.send(f"🎵 Now playing from playlist: **{playlist_name}**")

    await play_next()


@bot.event
async def on_reaction_add(reaction: discord.Reaction, user: discord.User):
    if user.bot:
        return


@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")


bot.run(os.environ["DISCORD_BOT_TOKEN"])
