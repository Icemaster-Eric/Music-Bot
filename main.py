import os
import asyncio
from random import shuffle
import discord
from discord.ext import commands


intents = discord.Intents.default()

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
thumbnails = {
    "Audrey's Theme": "https://hc-cdn.hel1.your-objectstorage.com/s/v3/c079c92ffafb34c2cf89f2f367d36b5d72d91c76_image.png",
    "Celestia's Theme": "https://hc-cdn.hel1.your-objectstorage.com/s/v3/0e1e678913ae712eb13fa031c0e4436032049225_image.png",
    "Eika's Theme": "https://hc-cdn.hel1.your-objectstorage.com/s/v3/6c8b65492bcac8a7035899eed3292d670dbc0a04_image.png",
    "Flavia's Theme": "https://hc-cdn.hel1.your-objectstorage.com/s/v3/f69850eb4bffa08cf134ec96e8559c89dd32a925_image.png",
    "Fuchsia's Theme": "https://hc-cdn.hel1.your-objectstorage.com/s/v3/ae27b3844f8a61e2f65f67ae0f6b87397e639767_image.png",
    "Kanami's Theme": "https://hc-cdn.hel1.your-objectstorage.com/s/v3/17ba1771592c38b0b4a1c906d7447093aa1ef9da_image.png",
    "Kokona's Theme": "https://hc-cdn.hel1.your-objectstorage.com/s/v3/3ed7fcfb2465e17b43ada66bb594c0c679bd2274_image.png",
    "Maddelena's Theme": "https://hc-cdn.hel1.your-objectstorage.com/s/v3/e48995ae19d646b2cc57a0dfce7c2f5df5f44f90_image.png",
    "Michele's Theme": "https://hc-cdn.hel1.your-objectstorage.com/s/v3/5d21d6188daa70fc53a1edc3f0a9cf831c9a941c_image.png",
    "Yvette's Theme": "https://hc-cdn.hel1.your-objectstorage.com/s/v3/3ae3150ee330eb2da43323e3c7e693bb7806c515_image.png",
    "Beautiful World": "https://hc-cdn.hel1.your-objectstorage.com/s/v3/37ddc9aa76abaabcce0b0cd593d27483fca0bf03_image.png",
    "strinova": "https://hc-cdn.hel1.your-objectstorage.com/s/v3/f71ea9118a610b5d1ca0f5241727c5524ff933ae_strinova_mjwu.jpg"
}


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
    embed.set_author(name=f"Music Playlist: {current_playlist_name.capitalize()}", icon_url="https://cdn-icons-png.flaticon.com/128/9325/9325026.png")
    embed.set_thumbnail(url=thumbnails.get(song_name, thumbnails["strinova"]))
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
        else:
            voice_client.resume()

    elif reaction.emoji == "⏭️":
        if voice_client.is_playing():
            voice_client.stop()

    elif reaction.emoji == "🔁":
        looping = not looping
        if song_message:
            embed = song_message.embeds[0]
            if looping:
                embed.set_footer(text="[Looping]")
            else:
                embed.remove_footer()
            song_message = await song_message.edit(embed=embed)

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
        embed.set_thumbnail(url=thumbnails.get(current_song_name, thumbnails["strinova"]))
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
