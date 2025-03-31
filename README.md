# wave103 discord music bot

wave103 is a discord bot designed to play music from youtube in voice channels. it uses the `discord.py` library for interacting with discord and `yt-dlp` for streaming audio from youtube.

## features

- play songs from youtube using search queries or direct urls.
- queue songs and manage the queue with commands like `!queue`, `!remove`, and `!clear`.
- skip, pause, resume, and stop songs.
- adjust the bot's playback volume.
- automatically plays the next song in the queue.

## commands

- **`!play <query>`**: plays the specified song in the voice channel. adds to the queue if a song is already playing.
- **`!play_next`**: plays the next song in the queue.
- **`!skip`**: skips the current song and plays the next one.
- **`!queue`**: displays the current song queue.
- **`!remove <num>`**: removes a song from the queue by its position.
- **`!clear`**: clears the entire song queue.
- **`!pause`**: pauses the current song.
- **`!resume`**: resumes the paused song.
- **`!volume <num>`**: changes the playback volume (1-100).
- **`!stop`**: stops playback and disconnects the bot from the voice channel.

## installation

1. clone the repository:
   ```bash
   git clone https://github.com/rinmz/wave103.git
   cd wave103