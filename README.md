# Strinova Music Bot
A Discord music bot that plays OSTs from Strinova, an anime-style third-person tactical competitive shooter. I made this bot so that I can listen to Strinova music while gaming.

The bot is very easy to use, featuring ergonomic commands, and only does what it needs to do - play Strinova OSTs. I oftentimes find that Discord bots include an overwhelming amount of repetitive features that are basically the same across different bots, and it leads to crowding the slash commands and making it unwieldy to use. This bot does its one and only job rather well, so here's a list of features:
- Use `/music` and the bot will join the voice channel you are currently in, starting the Strinova playlist and sending a message in your voice channel.
- The list of OSTs and the currently playing track are clearly shown in the message's embed, which is updated after each track.
- The message includes fast and responsive reaction controls for play/pause, skipping, shuffling, looping, and ending the playlist.

## Development Setup

1. Clone the repository and cd into the folder
2. Run `pip install -r requirements.txt`
3. Create a `.env` file with `DISCORD_BOT_TOKEN="your bot token"`
4. Run `main.py`
