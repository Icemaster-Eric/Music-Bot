import os
import asyncio
from random import shuffle
import discord
from discord.ext import commands


intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
voice_client: None | discord.VoiceClient = None

playlists_path = "playlists"
playlists = [name for name in os.listdir(playlists_path) if os.path.isdir(os.path.join(playlists_path, name))]
playlist = asyncio.Queue()
current_playlist_name = ""
current_song = ""
song_message: discord.Message | None = None
playlist_songs = []
looping = False


async def play_next():
    global song_message, looping, current_song

    if playlist.empty():
        if looping:
            for song in playlist_songs:
                await playlist.put(f"playlists/{current_playlist_name}/{song}")
        else:
            if voice_client is not None:
                if voice_client.is_connected():
                    await voice_client.disconnect()
                    await bot.change_presence(activity=None)
                    playlist_songs.clear()
                    song_message = None
                    looping = False
            return

    if voice_client is None:
        return

    song_path: str = await playlist.get()
    current_song = song_path.split("/")[-1]
    song_name = song_path.split("/")[-1][:-4].replace("_", " ")

    embed = discord.Embed(
        color=discord.Color.blurple(),
        title=f"Now Playing: {song_name}",
        description="\n".join([
            f"`{i + 1} {name.split('/')[-1][:-4].replace('_', ' ')}`" \
                if f"playlists/{current_playlist_name}/{name}" != song_path else \
                f"`[{i + 1}] {name.split('/')[-1][:-4].replace('_', ' ')}`" for i, name in enumerate(playlist_songs)
        ])
    )
    embed.set_author(name=f"Music Playlist: {current_playlist_name}", icon_url="https://cdn-icons-png.flaticon.com/128/9325/9325026.png")
    if looping:
        embed.set_footer(text="[Looping]")
    if song_message is not None:
        song_message = await song_message.edit(embed=embed)
    else:
        song_message = await voice_client.channel.send(embed=embed)

        for emoji in ["⏯️","⏭️","🔁","🔀","⏹️"]:
            await song_message.add_reaction(emoji)
    
    music_activity = discord.activity.Activity(
        name=song_name,
        type=discord.ActivityType.playing,
        state=f"in {voice_client.channel.name}"
    )
    await bot.change_presence(activity=music_activity)

    source = discord.FFmpegOpusAudio(song_path)
    voice_client.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(), bot.loop))


@bot.tree.command(name="music", description="Listen to Strinova OSTs in your VC")
async def play(interaction: discord.Interaction):
    global voice_client, current_playlist_name, song_message

    # Ensure the command user is in a voice channel.
    if interaction.user.voice is None: # type: ignore
        await interaction.response.send_message("You must join a voice channel to play music.", ephemeral=True)
        return

    if voice_client is not None:
        if voice_client.is_playing():
            await interaction.response.send_message("Already playing music in a voice channel.", ephemeral=True)
            return

    current_playlist_name = "strinova"

    # Defer the response since processing might take a moment.
    await interaction.response.defer()

    for mp3_file in os.listdir(f"playlists/strinova"):
        if mp3_file.endswith(".mp3"):
            playlist_songs.append(mp3_file)
            await playlist.put(f"playlists/strinova/{mp3_file}")

    voice_client = await interaction.user.voice.channel.connect() # type: ignore
    # reset song_message
    song_message = None

    await interaction.followup.send(f"🎵 Now playing from playlist: **Strinova**")
    await play_next()


@bot.event
async def on_reaction_add(reaction: discord.Reaction, user: discord.User):
    global looping, song_message, playlist_songs

    if user.bot:
        return

    message = reaction.message

    if message != song_message:
        return
    if not voice_client:
        return

    if reaction.emoji == "⏯️":
        if voice_client.is_playing():
            voice_client.pause()
            await voice_client.channel.send("> -# Paused current track", delete_after=10)
        else:
            voice_client.resume()
            await voice_client.channel.send("> -# Resumed current track", delete_after=10)

    elif reaction.emoji == "⏭️":
        if voice_client.is_playing():
            voice_client.stop()
            await voice_client.channel.send("> -# Skipped current track", delete_after=10)

    elif reaction.emoji == "🔁":
        looping = not looping
        if song_message:
            embed = song_message.embeds[0]
            if looping:
                embed.set_footer(text="[Looping]")
            else:
                embed.remove_footer()
            song_message = await song_message.edit(embed=embed)
        if looping:
            await voice_client.channel.send("> -# Looping current track", delete_after=10)
        else:
            await voice_client.channel.send("> -# Unlooping current track", delete_after=10)

    elif reaction.emoji == "🔀":
        shuffle(playlist_songs)

        while not playlist.empty():
            await playlist.get()
        
        current_song_name = current_song[:-4].replace("_", " ")

        i = 0
        for i, song_name in enumerate(playlist_songs):
            if song_name == current_song:
                break

        for next_song in playlist_songs[i+1:]:
            await playlist.put(f"playlists/{current_playlist_name}/{next_song}")

        embed = discord.Embed(
            color=discord.Color.blurple(),
            title=f"Now Playing: {current_song_name}",
            description="\n".join([
                f"`{i + 1} {name.split('/')[-1][:-4].replace('_', ' ')}`" \
                    if name != current_song else \
                    f"`[{i + 1}] {name.split('/')[-1][:-4].replace('_', ' ')}`" for i, name in enumerate(playlist_songs)
            ])
        )
        embed.set_author(name=f"Music Playlist: {current_playlist_name.capitalize()}", icon_url="https://cdn-icons-png.flaticon.com/128/9325/9325026.png")
        if looping:
            embed.set_footer(text="[Looping]")
        if song_message is not None:
            song_message = await song_message.edit(embed=embed)
        else:
            song_message = await voice_client.channel.send(embed=embed)

    elif reaction.emoji == "⏹️":
        await voice_client.disconnect()
        await bot.change_presence(activity=None)
        while not playlist.empty():
            await playlist.get()
        playlist_songs.clear()
        song_message = None
        looping = False

    await reaction.remove(user)


@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    global song_message, looping

    if member.bot:
        return

    if before.channel is not None:
        if voice_client is not None:
            # If no non-bot members remain in the channel, disconnect.
            if len([m for m in voice_client.channel.members if not m.bot]) == 0:
                await voice_client.disconnect()
                while not playlist.empty():
                    await playlist.get()
                playlist_songs.clear()
                song_message = None
                looping = False


@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")


bot.run(os.environ["DISCORD_BOT_TOKEN"])
