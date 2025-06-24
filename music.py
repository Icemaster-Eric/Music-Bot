import asyncio
import discord
from discord.ext import commands
import youtube_dl


# --- youtube_dl configuration ---
ytdl_format_options = {
    "format": "bestaudio/best",
    "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "restrictfilenames": True,
    "noplaylist": False,  # Allow playlist extraction.
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",  # Allow searching if a query is given.
}

ffmpeg_options = {
    "options": "-vn"  # -vn means no video.
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

# --- YTDLSource: a helper class to get an audio source ---
class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get("title")
        self.url = data.get("webpage_url")

    @classmethod
    async def from_url(cls, url_or_data, *, loop, stream=True):
        """
        If url_or_data is already a dict (pre-fetched info) then use it directly;
        otherwise, fetch the info from YouTube using youtube_dl.
        """
        if isinstance(url_or_data, dict):
            data = url_or_data
        else:
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url_or_data, download=not stream))
        # If data is a playlist, use the first entry.
        if "entries" in data:
            data = data["entries"][0]
        filename = data["url"] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

# --- MusicPlayer: manages a per-guild music queue and playback loop ---
class MusicPlayer:
    def __init__(self, bot: commands.Bot, voice_client: discord.VoiceClient):
        self.bot = bot
        self.voice_client = voice_client
        self.queue = asyncio.Queue()  # Queue holding youtube_dl info dictionaries.
        self.next = asyncio.Event()
        self.current = None
        # Create a task for the player loop.
        self.player_task = bot.loop.create_task(self.player_loop())

    async def player_loop(self):
        """Main player loop: waits for queued tracks and plays them."""
        while True:
            self.next.clear()
            try:
                # Wait for the next track. If nothing is queued for 5 minutes, time out.
                track = await asyncio.wait_for(self.queue.get(), timeout=300)
            except asyncio.TimeoutError:
                print("Queue inactive for 5 minutes; disconnecting.")
                await self.bot.change_presence(activity=None)
                await self.voice_client.disconnect()
                break

            # Before playing, check if there are any non-bot users in the channel.
            if not any(not member.bot for member in self.voice_client.channel.members):
                print("No non-bot users remain in the channel; disconnecting.")
                await self.bot.change_presence(activity=None)
                await self.voice_client.disconnect()
                break

            try:
                source = await YTDLSource.from_url(track, loop=self.bot.loop, stream=True)
            except Exception as e:
                print(f"Error processing track: {e}")
                continue

            self.current = source
            print(f"Now playing: {source.title}")
            music_activity = discord.activity.Activity(
                name=source.title,
                type=discord.ActivityType.playing,
                state=f"in {self.voice_client.channel.name}"
            )
            self.bot.loop.create_task(self.bot.change_presence(activity=music_activity))
            self.voice_client.play(source, after=lambda e: (print(f"Error while playing music: {e}"), self.bot.loop.call_soon_threadsafe(self.next.set)))
            # Wait until the track is finished (or skipped).
            await self.next.wait()
            await self.bot.change_presence(activity=None)
            self.current = None

            # After finishing a track, if the queue is empty and no one remains, disconnect.
            if self.queue.empty() and not any(not member.bot for member in self.voice_client.channel.members):
                print("Playback finished and no non-bot members remain; disconnecting.")
                await self.voice_client.disconnect()
                break
