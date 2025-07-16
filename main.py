import os
import asyncio
from random import shuffle
import discord
from discord.ext import commands

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Per-guild state containers
voice_clients: dict[int, discord.VoiceClient] = {}
queues: dict[int, asyncio.Queue[str]] = {}
playlist_songs: dict[int, list[str]] = {}
current_playlist_name: dict[int, str] = {}
current_song: dict[int, str] = {}
song_messages: dict[int, discord.Message] = {}
looping: dict[int, bool] = {}

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

async def play_next(guild_id: int):
    vc = voice_clients.get(guild_id)
    q = queues[guild_id]

    if q.empty():
        if looping[guild_id]:
            for song in playlist_songs[guild_id]:
                await q.put(f"playlists/{current_playlist_name[guild_id]}/{song}")
        else:
            if vc and vc.is_connected():
                await vc.disconnect()
            await bot.change_presence(activity=None)
            playlist_songs[guild_id].clear()
            song_messages.pop(guild_id, None)
            looping[guild_id] = False
            return

    if vc is None or not vc.is_connected():
        return

    song_path = await q.get()
    song_file = os.path.basename(song_path)
    current_song[guild_id] = song_file
    song_name = song_file[:-4].replace("_", " ")

    embed = discord.Embed(
        color=discord.Color.blurple(),
        title=f"Now Playing: {song_name}",
        description="\n".join(
            f"`[{i+1}] {name[:-4].replace('_',' ')}`" if name == song_file
            else f"`{i+1} {name[:-4].replace('_',' ')}`"
            for i, name in enumerate(playlist_songs[guild_id])
        )
    )
    embed.set_author(
        name=f"{current_playlist_name[guild_id].capitalize()} Playlist",
        icon_url="https://cdn-icons-png.flaticon.com/128/9325/9325026.png"
    )
    embed.set_thumbnail(url=thumbnails.get(song_name, thumbnails["strinova"]))
    if looping[guild_id]:
        embed.set_footer(text="[Looping]")

    msg = song_messages.get(guild_id)
    if msg:
        song_messages[guild_id] = await msg.edit(embed=embed)
    else:
        channel = vc.channel
        song_messages[guild_id] = await channel.send(embed=embed)
        for emoji in ["⏯️","⏮️","⏭️","🔁","🔀","⏹️"]:
            await song_messages[guild_id].add_reaction(emoji)

    activity = discord.Activity(
        name=song_name,
        type=discord.ActivityType.playing,
        state=f"in {vc.channel.name}"
    )
    await bot.change_presence(activity=activity)

    source = discord.FFmpegOpusAudio(song_path)
    vc.play(
        source,
        after=lambda e: asyncio.run_coroutine_threadsafe(play_next(guild_id), bot.loop)
    )

@bot.tree.command(name="music", description="Listen to an OST playlist in your VC")
async def music(interaction: discord.Interaction):
    guild_id = interaction.guild_id

    if not interaction.user.voice: # type: ignore
        await interaction.response.send_message(
            "You must join a voice channel first.", ephemeral=True
        )
        return

    elif voice_clients.get(guild_id) != None: # type: ignore
        if voice_clients.get(guild_id).is_connected(): # type: ignore
            await interaction.response.send_message(
                "Already playing in a voice channel.", ephemeral=True
            )
            return

    queues[guild_id] = queues.get(guild_id, asyncio.Queue()) # type: ignore
    playlist_songs[guild_id] = [] # type: ignore
    looping[guild_id] = False # type: ignore
    current_playlist_name[guild_id] = "strinova" # type: ignore

    base = f"playlists/strinova"
    for fn in os.listdir(base):
        if fn.endswith(".mp3"):
            playlist_songs[guild_id].append(fn) # type: ignore
            await queues[guild_id].put(f"{base}/{fn}") # type: ignore

    await interaction.response.defer()
    vc = await interaction.user.voice.channel.connect() # type: ignore
    voice_clients[guild_id] = vc # type: ignore

    await interaction.followup.send(f"🎵 Now playing in **{vc.channel.name}**")
    await play_next(guild_id) # type: ignore

@bot.event
async def on_reaction_add(reaction: discord.Reaction, user: discord.User):
    if user.bot:
        return
    msg = reaction.message
    guild_id = msg.guild.id if msg.guild else None
    if guild_id not in song_messages or msg.id != song_messages[guild_id].id:
        return

    vc = voice_clients.get(guild_id)
    q = queues[guild_id]

    emoji = reaction.emoji

    if emoji == "⏯️" and vc:
        if vc.is_playing(): vc.pause()
        else: vc.resume()

    elif emoji == "⏭️" and vc and vc.is_playing():
        vc.stop()

    elif emoji == "⏮️" and vc:
        # find index
        cur = current_song[guild_id]
        lst = playlist_songs[guild_id]
        try:
            idx = lst.index(cur)
        except ValueError:
            await reaction.remove(user)
            return

        if idx > 0:
            prev = idx - 1
        elif looping[guild_id]:
            prev = len(lst) - 1
        else:
            await reaction.remove(user)
            return

        while not q.empty(): await q.get()
        order = lst[prev:] + (lst[:prev] if looping[guild_id] else [])
        for s in order:
            await q.put(f"playlists/{current_playlist_name[guild_id]}/{s}")
        vc.stop()

    elif emoji == "🔁":
        looping[guild_id] = not looping[guild_id]
        embed = msg.embeds[0]
        if looping[guild_id]:
            embed.set_footer(text="[Looping]")
        else:
            embed.remove_footer()
        song_messages[guild_id] = await msg.edit(embed=embed)

    elif emoji == "🔀":
        lst = playlist_songs[guild_id]
        shuffle(lst)
        while not q.empty(): await q.get()
        cur = current_song[guild_id]
        i = lst.index(cur)
        for s in lst[i+1:]:
            await q.put(f"playlists/{current_playlist_name[guild_id]}/{s}")
        embed = discord.Embed(
            color=discord.Color.blurple(),
            title=f"Now Playing: {cur[:-4]}",
            description="\n".join(
                f"`[{i+1}] {name[:-4].replace('_',' ')}`" if name == cur
                else f"`{i+1} {name[:-4].replace('_',' ')}`"
                for i, name in enumerate(lst)
            )
        )
        embed.set_author(
            name=f"{current_playlist_name[guild_id].capitalize()} Playlist",
            icon_url="https://cdn-icons-png.flaticon.com/128/9325/9325026.png"
        )
        embed.set_thumbnail(url=thumbnails.get(cur[:-4], thumbnails["strinova"]))
        if looping[guild_id]:
            embed.set_footer(text="[Looping]")
        song_messages[guild_id] = await msg.edit(embed=embed)

    elif emoji == "⏹️" and vc:
        await vc.disconnect()
        await bot.change_presence(activity=None)
        queues[guild_id] = asyncio.Queue()
        playlist_songs[guild_id].clear()
        song_messages.pop(guild_id, None)
        looping[guild_id] = False

    await reaction.remove(user)

@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    guild_id = member.guild.id
    vc = voice_clients.get(guild_id)
    if vc and before.channel == vc.channel:
        non_bots = [m for m in vc.channel.members if not m.bot]
        if not non_bots:
            await vc.disconnect()
            queues[guild_id] = asyncio.Queue()
            playlist_songs[guild_id].clear()
            song_messages.pop(guild_id, None)
            looping[guild_id] = False

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

bot.run(os.environ["DISCORD_BOT_TOKEN"])
